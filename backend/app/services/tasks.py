from datetime import datetime
import asyncio
from typing import List
import json

from ..core.celery_app import celery_app
from ..core import scan_logger, main_logger, settings
from ..db.session import get_db_context
from ..db.models import Device, Metric, ScanLog, DeviceStatus
from .icmp_scanner import icmp_scanner
from .device_discovery import device_discovery

# Helper (duplicated to avoid circular imports or heavy refactor)
def resolve_hostname(ip_address: str):
    import socket
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        return hostname
    except:
        return None

@celery_app.task
def discover_subnet_task(subnet: str, add_discovered: bool = True):
    """
    Celery task to scan a subnet in the background.
    Uses asyncio.run() to execute the async scanner in the synchronous worker.
    Now includes enhanced device discovery for new devices.
    """
    scan_logger.info(f"TASK: Starting background subnet scan for {subnet}")
    
    # Run async logic in sync context
    async def _run_scan():
        return await icmp_scanner.scan_subnet(subnet)
        
    results, duration = asyncio.run(_run_scan())
    
    scan_logger.info(f"TASK: Scan complete. Processing {len(results)} results...")
    
    discovered_devices = []
    updated_devices = []
    unreachable_count = 0
    
    # Process results in DB
    with get_db_context() as db:
        for result in results:
            now = datetime.utcnow()
            
            # Check if device already exists
            existing = db.query(Device).filter(
                Device.ip_address == result.ip_address
            ).first()
            
            if result.is_reachable:
                hostname = resolve_hostname(result.ip_address)
                
                if not existing and add_discovered:
                    # Run enhanced discovery for NEW devices
                    try:
                        async def _discover(ip):
                            return await device_discovery.discover_device(ip, full_scan=True)
                        
                        details = asyncio.run(_discover(result.ip_address))
                        
                        # Use discovered info or fallback
                        final_hostname = details.hostname or details.netbios_name or hostname
                        vendor = details.vendor
                        os_type = details.os_type
                        
                        # Store open ports as JSON string
                        open_ports = json.dumps(details.open_ports) if details.open_ports else None
                        
                        scan_logger.info(f"Enhanced discovery for {result.ip_address}: vendor={vendor}, os={os_type}, ports={len(details.open_ports)}")
                        
                    except Exception as e:
                        scan_logger.warning(f"Enhanced discovery failed for {result.ip_address}: {e}")
                        final_hostname = hostname
                        vendor = None
                        os_type = None
                        open_ports = None
                    
                    # Create new device with enhanced info
                    device = Device(
                        ip_address=result.ip_address,
                        hostname=final_hostname,
                        vendor=vendor,
                        os_type=os_type,
                        mac_address=getattr(details, 'mac_address', None) if 'details' in dir() else None,
                        status=DeviceStatus.UP,
                        last_seen=now,
                        consecutive_failures=0,
                        created_at=now,
                        updated_at=now
                    )
                    db.add(device)
                    db.flush()
                    
                    # Initial metric
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
                    # Update
                    existing.last_seen = now
                    existing.consecutive_failures = 0
                    existing.status = DeviceStatus.UP # Reset status
                    existing.updated_at = now
                    if hostname: existing.hostname = hostname
                    
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
                if existing:
                    existing.consecutive_failures = (existing.consecutive_failures or 0) + 1
                    existing.updated_at = now
        
        # Log completion
        scan_log = ScanLog(
            action="DISCOVERY_TASK",
            details=f"Background Scan: {subnet} - {len(discovered_devices)} new",
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
        "subnet": subnet, 
        "new": len(discovered_devices), 
        "updated": len(updated_devices)
    }
