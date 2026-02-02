"""
Device API Routes.
Endpoints for managing monitored devices.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db.session import get_db
from ..db.models import Device, Metric, DeviceStatus, Alert
from ..api.schemas import (
    DeviceCreate, DeviceUpdate, DeviceResponse, DeviceWithMetrics
)

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=List[DeviceWithMetrics])
async def list_devices(
    status: Optional[DeviceStatus] = Query(None, description="Filter by status"),
    is_active: Optional[bool] = Query(None, description="Filter by active state"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    List all monitored devices with optional filtering.
    Includes latest metrics for each device.
    """
    query = db.query(Device)
    
    if status:
        query = query.filter(Device.status == status)
    if is_active is not None:
        query = query.filter(Device.is_active == is_active)
    
    devices = query.offset(skip).limit(limit).all()
    
    # Enrich with latest metrics
    result = []
    for device in devices:
        device_data = DeviceWithMetrics.model_validate(device)
        
        # Get latest metric
        latest_metric = db.query(Metric).filter(
            Metric.device_id == device.id
        ).order_by(Metric.timestamp.desc()).first()
        
        if latest_metric:
            device_data.latest_latency_ms = latest_metric.latency_ms
            device_data.latest_packet_loss = latest_metric.packet_loss_percent
            device_data.latest_cpu_usage = latest_metric.cpu_usage_percent
        
        result.append(device_data)
    
    return result


# NOTE: Static routes MUST come before dynamic /{device_id} routes
@router.get("/summary/stats")
async def get_device_stats(db: Session = Depends(get_db)):
    """Get summary statistics for all devices."""
    total = db.query(Device).count()
    active = db.query(Device).filter(Device.is_active == True).count()
    
    status_counts = db.query(
        Device.status,
        func.count(Device.id)
    ).group_by(Device.status).all()
    
    stats = {
        "total_devices": total,
        "active_devices": active,
        "status_breakdown": {str(status): count for status, count in status_counts}
    }
    
    return stats


@router.delete("/all", status_code=200)
async def delete_all_devices(
    confirm: bool = Query(False, description="Must be true to confirm deletion"),
    db: Session = Depends(get_db)
):
    """
    Delete ALL devices and their metrics/alerts.
    Useful for resetting the system during testing.
    Requires confirm=true query parameter.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Add ?confirm=true to confirm deletion of all devices"
        )
    
    # Delete alerts first (foreign key)
    alerts_deleted = db.query(Alert).delete()
    
    # Delete all metrics (foreign key)
    metrics_deleted = db.query(Metric).delete()
    
    # Then devices
    devices_deleted = db.query(Device).delete()
    
    db.commit()
    
    return {
        "message": "All devices deleted",
        "devices_deleted": devices_deleted,
        "metrics_deleted": metrics_deleted,
        "alerts_deleted": alerts_deleted
    }


# Dynamic routes with {device_id} parameter
@router.get("/{device_id}", response_model=DeviceWithMetrics)
async def get_device(
    device_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific device by ID with latest metrics."""
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device_data = DeviceWithMetrics.model_validate(device)
    
    latest_metric = db.query(Metric).filter(
        Metric.device_id == device.id
    ).order_by(Metric.timestamp.desc()).first()
    
    if latest_metric:
        device_data.latest_latency_ms = latest_metric.latency_ms
        device_data.latest_packet_loss = latest_metric.packet_loss_percent
        device_data.latest_cpu_usage = latest_metric.cpu_usage_percent
    
    return device_data


@router.post("", response_model=DeviceResponse, status_code=201)
async def create_device(
    device_data: DeviceCreate,
    db: Session = Depends(get_db)
):
    """Add a new device to monitoring."""
    # Check for duplicate IP
    existing = db.query(Device).filter(
        Device.ip_address == device_data.ip_address
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Device with IP {device_data.ip_address} already exists"
        )
    
    device = Device(**device_data.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    
    return device


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int,
    device_data: DeviceUpdate,
    db: Session = Depends(get_db)
):
    """Update device configuration."""
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Update only provided fields
    update_data = device_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)
    
    device.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(device)
    
    return device


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: int,
    db: Session = Depends(get_db)
):
    """Remove a device from monitoring."""
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    db.delete(device)
    db.commit()
    
    return None
