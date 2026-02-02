"""
Discovery API Routes.
Endpoints for enhanced device discovery with MAC, vendor, OS detection, and port scanning.
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import Device
from ..api.schemas import DeviceDiscoveryRequest, DeviceDiscoveryResponse
from ..services.device_discovery import device_discovery

router = APIRouter(prefix="/discovery", tags=["Discovery"])


@router.post("/device", response_model=DeviceDiscoveryResponse)
async def discover_device(
    request: DeviceDiscoveryRequest,
    db: Session = Depends(get_db)
):
    """
    Discover detailed information about a device from its IP address.
    
    Retrieves:
    - MAC address (via ARP)
    - Vendor/manufacturer (via OUI database)
    - Operating system (via TTL analysis)
    - Open ports (via TCP scan)
    - Hostname (via DNS)
    - NetBIOS name (Windows only)
    """
    try:
        details = await device_discovery.discover_device(
            request.ip_address,
            full_scan=request.full_scan
        )
        
        return DeviceDiscoveryResponse(
            ip_address=details.ip_address,
            mac_address=details.mac_address,
            vendor=details.vendor,
            os_type=details.os_type,
            os_confidence=details.os_confidence,
            hostname=details.hostname,
            netbios_name=details.netbios_name,
            open_ports=details.open_ports,
            ttl=details.ttl,
            discovery_time_seconds=details.discovery_time_seconds
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/device/{device_id}/enrich")
async def enrich_device(
    device_id: int,
    full_scan: bool = True,
    db: Session = Depends(get_db)
):
    """
    Enrich an existing device with discovered details.
    Updates the device record with MAC, vendor, OS, and port information.
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    try:
        details = await device_discovery.discover_device(
            device.ip_address,
            full_scan=full_scan
        )
        
        # Update device with discovered details
        if details.mac_address:
            device.mac_address = details.mac_address
        if details.vendor:
            device.vendor = details.vendor
        if details.os_type:
            device.os_type = details.os_type
        if not device.hostname and details.hostname:
            device.hostname = details.hostname
        if details.open_ports:
            device.open_ports = json.dumps(details.open_ports)
        
        db.commit()
        db.refresh(device)
        
        return {
            "message": "Device enriched successfully",
            "device_id": device.id,
            "ip_address": device.ip_address,
            "mac_address": details.mac_address,
            "vendor": details.vendor,
            "os_type": details.os_type,
            "hostname": details.hostname,
            "open_ports": details.open_ports,
            "discovery_time_seconds": details.discovery_time_seconds
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enrich-all")
async def enrich_all_devices(
    full_scan: bool = False,
    db: Session = Depends(get_db)
):
    """
    Enrich all active devices with discovered details.
    This can take a while for many devices.
    """
    devices = db.query(Device).filter(Device.is_active == True).all()
    
    results = {
        "total_devices": len(devices),
        "enriched": 0,
        "failed": 0,
        "details": []
    }
    
    for device in devices:
        try:
            details = await device_discovery.discover_device(
                device.ip_address,
                full_scan=full_scan
            )
            
            # Update device
            if details.mac_address:
                device.mac_address = details.mac_address
            if details.vendor:
                device.vendor = details.vendor
            if details.os_type:
                device.os_type = details.os_type
            if not device.hostname and details.hostname:
                device.hostname = details.hostname
            if details.open_ports:
                device.open_ports = json.dumps(details.open_ports)
            
            results["enriched"] += 1
            results["details"].append({
                "ip": device.ip_address,
                "status": "success",
                "vendor": details.vendor,
                "os": details.os_type
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "ip": device.ip_address,
                "status": "failed",
                "error": str(e)
            })
    
    db.commit()
    
    db.commit()
    
    return results


@router.get("/local-network")
async def get_local_network():
    """
    Get the local network information (IP and subnet).
    Used to pre-fill the discovery subnet field.
    """
    return await device_discovery.get_local_network_info()
