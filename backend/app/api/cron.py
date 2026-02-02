"""
Cron Job Handler for Vercel Scheduled Tasks.
Triggers automatic health checks on all monitored devices.
"""

import os
from datetime import datetime
from fastapi import APIRouter, Header, HTTPException
from app.db.session import get_db_context
from app.db.models import Device, Metric, DeviceStatus
from app.services.icmp_scanner import icmp_scanner
from app.core import main_logger

router = APIRouter()

# Secret for cron authentication (set in Vercel environment)
CRON_SECRET = os.getenv("CRON_SECRET", "")

@router.get("/cron/health-check")
async def cron_health_check(
    authorization: str = Header(default=None)
):
    """
    Vercel Cron endpoint - triggers health check for all active devices.
    Called automatically every 5 minutes by Vercel Cron.
    
    Security: Vercel includes a secret header for cron jobs.
    """
    # Verify cron secret in production
    if CRON_SECRET and authorization != f"Bearer {CRON_SECRET}":
        # In development, allow without auth
        if os.getenv("VERCEL"):
            raise HTTPException(status_code=401, detail="Unauthorized cron request")
    
    main_logger.info("Cron job triggered: Starting scheduled health check")
    
    try:
        with get_db_context() as db:
            # Get all active devices
            devices = db.query(Device).filter(Device.is_active == True).all()
            
            if not devices:
                return {
                    "status": "success",
                    "message": "No active devices to check",
                    "devices_checked": 0
                }
            
            results = {
                "total": len(devices),
                "up": 0,
                "down": 0,
                "errors": 0
            }
            
            now = datetime.utcnow()
            
            for device in devices:
                try:
                    # Use ICMP scanner for ping check
                    ping_result = await icmp_scanner.ping(device.ip_address)
                    
                    if ping_result.is_reachable:
                        device.status = DeviceStatus.UP
                        device.last_seen = now
                        device.consecutive_failures = 0
                        results["up"] += 1
                        
                        # Record metric
                        metric = Metric(
                            device_id=device.id,
                            timestamp=now,
                            latency_ms=ping_result.latency_ms,
                            packet_loss_percent=ping_result.packet_loss_percent,
                            packets_sent=ping_result.packets_sent,
                            packets_received=ping_result.packets_received
                        )
                        db.add(metric)
                    else:
                        device.consecutive_failures = (device.consecutive_failures or 0) + 1
                        if device.consecutive_failures >= 3:
                            device.status = DeviceStatus.DOWN
                        results["down"] += 1
                    
                    device.updated_at = now
                    
                except Exception as e:
                    main_logger.error(f"Health check failed for {device.ip_address}: {e}")
                    results["errors"] += 1
            
            db.commit()
            
            main_logger.info(f"Cron health check complete: {results}")
            
            return {
                "status": "success",
                "message": "Health check completed",
                "devices_checked": results["total"],
                "devices_up": results["up"],
                "devices_down": results["down"],
                "errors": results["errors"]
            }
            
    except Exception as e:
        main_logger.error(f"Cron health check failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

