from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import socket
import struct
import asyncio

from app.db.session import get_db
from sqlalchemy.orm import Session
from app.db.models import Device

from app.core.audit import audit_action
from app.services.device_discovery import device_discovery

router = APIRouter()

class SSHTestRequest(BaseModel):
    ip: str
    username: str
    password: str
    port: int = 22

class WOLRequest(BaseModel):
    mac_address: str
    broadcast_ip: str = "255.255.255.255"

@router.post("/wol")
@audit_action("WAKE_DEVICE", resource_field="mac_address")
async def wake_on_lan(request: WOLRequest):
    """
    Send a Wake-on-LAN magic packet.
    """
    try:
        # Clean and validate MAC format
        mac_clean = request.mac_address.replace(":", "").replace("-", "").replace(".", "").upper()
        
        if len(mac_clean) != 12:
            raise ValueError(f"Invalid MAC address format: {request.mac_address}")
        
        # Validate hex characters
        if not all(c in '0123456789ABCDEF' for c in mac_clean):
            raise ValueError("MAC address contains invalid characters")

        # Build magic packet: 6 x 0xFF + 16 x MAC address
        data = bytes.fromhex("FF" * 6 + mac_clean * 16)
        
        # Send packet
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(data, (request.broadcast_ip, 9))
            
        return {
            "status": "success", 
            "message": f"Magic packet sent to {request.mac_address}",
            "mac_clean": mac_clean
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wol/device/{device_id}")
async def wake_device_by_id(
    device_id: int,
    broadcast_ip: str = "255.255.255.255",
    db: Session = Depends(get_db)
):
    """
    Send Wake-on-LAN magic packet to a device by its ID.
    Device must have a MAC address stored.
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if not device.mac_address:
        raise HTTPException(
            status_code=400, 
            detail=f"Device {device.ip_address} has no MAC address. Run device discovery first."
        )
    
    # Send WoL packet
    request = WOLRequest(mac_address=device.mac_address, broadcast_ip=broadcast_ip)
    return await wake_on_lan(request)


@router.post("/enrich/{device_id}")
async def enrich_device(
    device_id: int,
    full_scan: bool = True,
    db: Session = Depends(get_db)
):
    """
    Re-discover and enrich device details (MAC, vendor, OS, ports).
    Updates the device in the database with discovered information.
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    try:
        # Run device discovery
        details = await device_discovery.discover_device(device.ip_address, full_scan=full_scan)
        
        # Update device with discovered information
        if details.mac_address:
            device.mac_address = details.mac_address
        if details.vendor:
            device.vendor = details.vendor
        if details.os_type:
            device.os_type = details.os_type
        if details.hostname:
            device.hostname = details.hostname
        if details.open_ports:
            import json
            device.open_ports = json.dumps(details.open_ports)
        
        db.commit()
        
        return {
            "status": "success",
            "device_id": device_id,
            "ip_address": device.ip_address,
            "mac_address": details.mac_address,
            "vendor": details.vendor,
            "os_type": details.os_type,
            "hostname": details.hostname,
            "open_ports_count": len(details.open_ports),
            "discovery_time": round(details.discovery_time_seconds, 2)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


@router.post("/ssh/test")
@audit_action("SSH_TEST", resource_field="ip")
async def test_ssh_connection(request: SSHTestRequest):
    """
    Test SSH connectivity.
    Note: Basic socket check for now to avoid heavy paramiko dependency in serverless.
    """
    try:
        # Simple TCP connect check first
        future = asyncio.open_connection(request.ip, request.port)
        reader, writer = await asyncio.wait_for(future, timeout=3.0)
        writer.close()
        await writer.wait_closed()
        
        return {
            "status": "success", 
            "message": f"Port {request.port} is open. SSH service available.",
            "details": "Credential validation requires full SSH client (not available in lite mode)"
        }
    except Exception as e:
        return {"status": "error", "message": f"Connection failed: {str(e)}"}

