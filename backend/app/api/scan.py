"""
Scan API Routes.
Endpoints for triggering and viewing scan operations.
Now includes synchronous scan option for immediate results.
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import ScanLog, Device, Metric, DeviceStatus
from ..api.schemas import ScanRequest, ScanLogResponse
from ..services.monitoring import monitoring_orchestrator
from ..services.icmp_scanner import icmp_scanner

router = APIRouter(prefix="/scan", tags=["Scanning"])


def resolve_hostname(ip_address: str):
    """Helper to resolve hostname from IP."""
    import socket
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        return hostname
    except:
        return None


@router.post("/discover")
async def discover_subnet(
    request: ScanRequest,
    db: Session = Depends(get_db)
):
    """
    Trigger a network discovery scan on a subnet.
    Runs synchronously and returns results immediately.
    """
    try:
        # Run scan synchronously for immediate results
        results, duration = await icmp_scanner.scan_subnet(request.subnet)
        
        discovered_devices = []
        updated_devices = []
        unreachable_count = 0
        now = datetime.utcnow()
        
        for result in results:
            if result.is_reachable:
                # Check if device already exists
                existing = db.query(Device).filter(
                    Device.ip_address == result.ip_address
                ).first()
                
                hostname = resolve_hostname(result.ip_address)
                
                if not existing and request.add_discovered:
                    # Create new device
                    device = Device(
                        ip_address=result.ip_address,
                        hostname=hostname,
                        status=DeviceStatus.UP,
                        last_seen=now,
                        consecutive_failures=0,
                        created_at=now,
                        updated_at=now
                    )
                    db.add(device)
                    db.flush()
                    
                    # Add metric
                    metric = Metric(
                        device_id=device.id,
                        timestamp=now,
                        latency_ms=result.latency_ms,
                        packet_loss_percent=result.packet_loss_percent,
                        packets_sent=result.packets_sent,
                        packets_received=result.packets_received
                    )
                    db.add(metric)
                    discovered_devices.append(result.ip_address)
                    
                elif existing:
                    # Update existing device
                    existing.last_seen = now
                    existing.consecutive_failures = 0
                    existing.status = DeviceStatus.UP
                    existing.updated_at = now
                    if hostname:
                        existing.hostname = hostname
                    
                    metric = Metric(
                        device_id=existing.id,
                        timestamp=now,
                        latency_ms=result.latency_ms,
                        packet_loss_percent=result.packet_loss_percent,
                        packets_sent=result.packets_sent,
                        packets_received=result.packets_received
                    )
                    db.add(metric)
                    updated_devices.append(result.ip_address)
            else:
                unreachable_count += 1
                # Update existing device status if down
                existing = db.query(Device).filter(
                    Device.ip_address == result.ip_address
                ).first()
                if existing:
                    existing.consecutive_failures = (existing.consecutive_failures or 0) + 1
                    if existing.consecutive_failures >= 3:
                        existing.status = DeviceStatus.DOWN
                    existing.updated_at = now
        
        # Log the scan
        scan_log = ScanLog(
            action="DISCOVERY",
            details=f"Subnet scan: {request.subnet}",
            devices_scanned=len(results),
            devices_up=len(discovered_devices) + len(updated_devices),
            devices_down=unreachable_count,
            duration_seconds=duration,
            success=True
        )
        db.add(scan_log)
        db.commit()
        
        return {
            "status": "completed",
            "message": f"Scan complete - found {len(discovered_devices) + len(updated_devices)} reachable hosts",
            "subnet": request.subnet,
            "reachable_hosts": len(discovered_devices) + len(updated_devices),
            "new_devices_added": len(discovered_devices),
            "devices_updated": len(updated_devices),
            "unreachable": unreachable_count,
            "total_scanned": len(results),
            "duration_seconds": round(duration, 2)
        }
        
    except Exception as e:
        # Log failed scan
        scan_log = ScanLog(
            action="DISCOVERY",
            details=f"Failed: {request.subnet}",
            success=False,
            error_message=str(e)
        )
        db.add(scan_log)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health-check")
async def trigger_health_check(
    db: Session = Depends(get_db)
):
    """
    Trigger an immediate health check on all monitored devices.
    """
    try:
        result = await monitoring_orchestrator.run_health_check(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ping/{ip_address}")
async def ping_single_host(
    ip_address: str,
    db: Session = Depends(get_db)
):
    """
    Ping a single IP address and return the result.
    Useful for quick connectivity tests.
    """
    try:
        result = await icmp_scanner.ping_host_async(ip_address)
        
        return {
            "ip_address": result.ip_address,
            "is_reachable": result.is_reachable,
            "latency_ms": result.latency_ms,
            "packet_loss_percent": result.packet_loss_percent,
            "packets_sent": result.packets_sent,
            "packets_received": result.packets_received,
            "error": result.error_message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs", response_model=List[ScanLogResponse])
async def get_scan_logs(
    action: str = Query(None, description="Filter by action type"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get recent scan operation logs.
    """
    query = db.query(ScanLog)
    
    if action:
        query = query.filter(ScanLog.action == action)
    
    logs = query.order_by(ScanLog.timestamp.desc()).limit(limit).all()
    
    return logs


@router.get("/logs/latest", response_model=ScanLogResponse)
async def get_latest_scan(
    db: Session = Depends(get_db)
):
    """Get the most recent scan log entry."""
    log = db.query(ScanLog).order_by(ScanLog.timestamp.desc()).first()
    
    if not log:
        raise HTTPException(status_code=404, detail="No scan logs found")
    
    return log

