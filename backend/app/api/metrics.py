"""
Metrics API Routes.
Endpoints for retrieving device performance metrics.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db.session import get_db
from ..db.models import Device, Metric
from ..api.schemas import MetricResponse

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/{device_id}", response_model=List[MetricResponse])
async def get_device_metrics(
    device_id: int,
    hours: int = Query(24, ge=1, le=720, description="Hours of history"),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db)
):
    """
    Get historical metrics for a device.
    Returns metrics from the last N hours.
    """
    # Verify device exists
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Calculate time range
    since = datetime.utcnow() - timedelta(hours=hours)
    
    metrics = db.query(Metric).filter(
        Metric.device_id == device_id,
        Metric.timestamp >= since
    ).order_by(Metric.timestamp.desc()).limit(limit).all()
    
    return metrics


@router.get("/{device_id}/latest", response_model=Optional[MetricResponse])
async def get_latest_metric(
    device_id: int,
    db: Session = Depends(get_db)
):
    """Get the most recent metric for a device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    metric = db.query(Metric).filter(
        Metric.device_id == device_id
    ).order_by(Metric.timestamp.desc()).first()
    
    return metric


@router.get("/{device_id}/summary")
async def get_metrics_summary(
    device_id: int,
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db)
):
    """
    Get aggregated metrics summary for a device.
    Includes min, max, and average values.
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Aggregate latency
    latency_stats = db.query(
        func.min(Metric.latency_ms).label("min"),
        func.max(Metric.latency_ms).label("max"),
        func.avg(Metric.latency_ms).label("avg"),
        func.count(Metric.id).label("count")
    ).filter(
        Metric.device_id == device_id,
        Metric.timestamp >= since,
        Metric.latency_ms.isnot(None)
    ).first()
    
    # Aggregate packet loss
    loss_stats = db.query(
        func.min(Metric.packet_loss_percent).label("min"),
        func.max(Metric.packet_loss_percent).label("max"),
        func.avg(Metric.packet_loss_percent).label("avg")
    ).filter(
        Metric.device_id == device_id,
        Metric.timestamp >= since
    ).first()
    
    # Aggregate CPU (if available)
    cpu_stats = db.query(
        func.min(Metric.cpu_usage_percent).label("min"),
        func.max(Metric.cpu_usage_percent).label("max"),
        func.avg(Metric.cpu_usage_percent).label("avg")
    ).filter(
        Metric.device_id == device_id,
        Metric.timestamp >= since,
        Metric.cpu_usage_percent.isnot(None)
    ).first()
    
    return {
        "device_id": device_id,
        "period_hours": hours,
        "sample_count": latency_stats.count if latency_stats else 0,
        "latency_ms": {
            "min": latency_stats.min if latency_stats else None,
            "max": latency_stats.max if latency_stats else None,
            "avg": round(latency_stats.avg, 2) if latency_stats and latency_stats.avg else None
        },
        "packet_loss_percent": {
            "min": loss_stats.min if loss_stats else None,
            "max": loss_stats.max if loss_stats else None,
            "avg": round(loss_stats.avg, 2) if loss_stats and loss_stats.avg else None
        },
        "cpu_usage_percent": {
            "min": cpu_stats.min if cpu_stats else None,
            "max": cpu_stats.max if cpu_stats else None,
            "avg": round(cpu_stats.avg, 2) if cpu_stats and cpu_stats.avg else None
        }
    }
