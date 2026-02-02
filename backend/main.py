"""
Mini NOC Backend - FastAPI Application Entry Point.
Network Monitoring & Fault Detection System.
"""

from contextlib import asynccontextmanager
from datetime import datetime
import time
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app, Counter, Histogram

from app.core import settings, main_logger
from app.db.session import init_db, get_db
from app.api import devices, metrics, alerts, scan, discovery, notifications, analytics, web_monitor, control, health, cron, incidents
from app.api.schemas import DashboardSummary
from app.db.models import Device, Alert, ScanLog, DeviceStatus, AlertSeverity
from app.services.monitoring import monitoring_orchestrator
from sqlalchemy.orm import Session

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    # Startup
    main_logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db()
    main_logger.info("Database initialized")
    
    # Start background monitoring (Skip on Vercel serverless)
    import os
    if not os.getenv("VERCEL"):
        monitoring_orchestrator.start_background_monitoring()
    
    yield
    
    # Shutdown
    main_logger.info("Shutting down Mini NOC")
    if not os.getenv("VERCEL"):
        monitoring_orchestrator.stop_background_monitoring()


# Create FastAPI application with enhanced OpenAPI docs
app = FastAPI(
    title="Mini NOC API",
    description="""
## Network Operations Center API

Enterprise-grade network monitoring system for:
- **Device Management**: Add, monitor, and manage network devices
- **Health Checks**: Automated ICMP ping and port scanning
- **Alerts**: Real-time alerting with severity levels
- **Incidents**: Track and manage network incidents with timeline
- **Analytics**: SLA metrics, uptime tracking, and export reports

### Authentication
Currently open API - rate limited to 100 requests/minute per IP.

### Quick Links
- [Dashboard](/docs) - This page
- [Health Check](/health) - API health status
- [Metrics](/metrics) - Prometheus metrics
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Devices", "description": "Device management operations"},
        {"name": "Scanning", "description": "Network discovery and health checks"},
        {"name": "Alerts", "description": "Alert management"},
        {"name": "incidents", "description": "Incident tracking and timeline"},
        {"name": "analytics", "description": "SLA metrics and reporting"},
        {"name": "Health", "description": "API health and status"},
    ],
    lifespan=lifespan
)

# Prometheus Metrics
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"])

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        raise e
    finally:
        duration = time.time() - start_time
        path = request.url.path
        if path != "/metrics" and path != "/health":
            REQUEST_COUNT.labels(method=request.method, endpoint=path, status=status_code).inc()
            REQUEST_LATENCY.labels(method=request.method, endpoint=path).observe(duration)
    
    return response

# Rate Limiting Configuration
from collections import defaultdict
import asyncio

class RateLimiter:
    """Simple in-memory rate limiter (100 requests per minute per IP)."""
    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > minute_ago]
        
        # Check if under limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return False
        
        # Record this request
        self.requests[client_ip].append(now)
        return True

rate_limiter = RateLimiter(requests_per_minute=100)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting: 100 requests per minute per IP."""
    # Skip rate limiting for health and metrics
    if request.url.path in ["/health", "/metrics"]:
        return await call_next(request)
    
    client_ip = request.client.host if request.client else "unknown"
    
    if not rate_limiter.is_allowed(client_ip):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please try again later."}
        )
    
    return await call_next(request)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    # Content Security Policy (relaxed for API)
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
    
    # HSTS (enable in production with HTTPS)
    # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

# CORS
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include API routers
app.include_router(health.router, tags=["Health"]) # Watchdog
app.include_router(scan.router, prefix="/api") 
app.include_router(devices.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(discovery.router, prefix="/api", tags=["discovery"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(web_monitor.router, prefix="/api/web", tags=["web_monitor"])
app.include_router(control.router, prefix="/api/control", tags=["control"])
app.include_router(cron.router, prefix="/api", tags=["cron"])
app.include_router(incidents.router, prefix="/api/incidents", tags=["incidents"])


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }


@app.get("/api/dashboard/summary", response_model=DashboardSummary, tags=["Dashboard"])
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Get complete dashboard summary statistics.
    Used by the frontend for the main dashboard view.
    """
    # Device counts by status
    total_devices = db.query(Device).filter(Device.is_active == True).count()
    
    devices_up = db.query(Device).filter(
        Device.is_active == True,
        Device.status == DeviceStatus.UP
    ).count()
    
    devices_down = db.query(Device).filter(
        Device.is_active == True,
        Device.status == DeviceStatus.DOWN
    ).count()
    
    devices_degraded = db.query(Device).filter(
        Device.is_active == True,
        Device.status == DeviceStatus.DEGRADED
    ).count()
    
    devices_unknown = db.query(Device).filter(
        Device.is_active == True,
        Device.status == DeviceStatus.UNKNOWN
    ).count()
    
    # Alert counts
    active_alerts = db.query(Alert).filter(Alert.is_resolved == False).count()
    
    critical_alerts = db.query(Alert).filter(
        Alert.is_resolved == False,
        Alert.severity == AlertSeverity.CRITICAL
    ).count()
    
    warning_alerts = db.query(Alert).filter(
        Alert.is_resolved == False,
        Alert.severity == AlertSeverity.WARNING
    ).count()
    
    # Last scan timestamp
    last_scan_log = db.query(ScanLog).order_by(ScanLog.timestamp.desc()).first()
    last_scan = last_scan_log.timestamp if last_scan_log else None
    
    return DashboardSummary(
        total_devices=total_devices,
        devices_up=devices_up,
        devices_down=devices_down,
        devices_degraded=devices_degraded,
        devices_unknown=devices_unknown,
        active_alerts=active_alerts,
        critical_alerts=critical_alerts,
        warning_alerts=warning_alerts,
        last_scan=last_scan
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
