"""
Alerts API Routes.
Endpoints for viewing and managing alerts.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from ..db.session import get_db
from ..db.models import Alert, Device, AlertSeverity
from ..api.schemas import AlertResponse, AlertResolve

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    severity: Optional[AlertSeverity] = Query(None, description="Filter by severity"),
    device_id: Optional[int] = Query(None, description="Filter by device"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    List alerts with optional filtering.
    Returns alerts sorted by creation time (newest first).
    """
    query = db.query(Alert).options(joinedload(Alert.device))
    
    if resolved is not None:
        query = query.filter(Alert.is_resolved == resolved)
    if severity:
        query = query.filter(Alert.severity == severity)
    if device_id:
        query = query.filter(Alert.device_id == device_id)
    
    alerts = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()
    
    # Add device IP to response
    result = []
    for alert in alerts:
        alert_data = AlertResponse.model_validate(alert)
        if alert.device:
            alert_data.device_ip = alert.device.ip_address
        result.append(alert_data)
    
    return result


@router.get("/active", response_model=List[AlertResponse])
async def get_active_alerts(
    db: Session = Depends(get_db)
):
    """Get all unresolved alerts."""
    alerts = db.query(Alert).options(
        joinedload(Alert.device)
    ).filter(
        Alert.is_resolved == False
    ).order_by(Alert.created_at.desc()).all()
    
    result = []
    for alert in alerts:
        alert_data = AlertResponse.model_validate(alert)
        if alert.device:
            alert_data.device_ip = alert.device.ip_address
        result.append(alert_data)
    
    return result


@router.get("/summary")
async def get_alert_summary(db: Session = Depends(get_db)):
    """Get summary of alerts grouped by severity."""
    active_counts = db.query(
        Alert.severity,
        func.count(Alert.id)
    ).filter(
        Alert.is_resolved == False
    ).group_by(Alert.severity).all()
    
    total_active = sum(count for _, count in active_counts)
    
    return {
        "total_active": total_active,
        "by_severity": {str(sev): count for sev, count in active_counts},
        "critical": next((c for s, c in active_counts if s == AlertSeverity.CRITICAL), 0),
        "warning": next((c for s, c in active_counts if s == AlertSeverity.WARNING), 0),
        "info": next((c for s, c in active_counts if s == AlertSeverity.INFO), 0)
    }


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific alert by ID."""
    alert = db.query(Alert).options(
        joinedload(Alert.device)
    ).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert_data = AlertResponse.model_validate(alert)
    if alert.device:
        alert_data.device_ip = alert.device.ip_address
    
    return alert_data


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: int,
    resolve_data: AlertResolve,
    db: Session = Depends(get_db)
):
    """Mark an alert as resolved or unresolve it."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.is_resolved = resolve_data.is_resolved
    if resolve_data.is_resolved:
        alert.resolved_at = datetime.utcnow()
    else:
        alert.resolved_at = None
    
    db.commit()
    db.refresh(alert)
    
    return alert


@router.post("/resolve-all", status_code=200)
async def resolve_all_alerts(
    severity: Optional[AlertSeverity] = Query(None),
    device_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Bulk resolve alerts matching the filter criteria."""
    query = db.query(Alert).filter(Alert.is_resolved == False)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    if device_id:
        query = query.filter(Alert.device_id == device_id)
    
    count = query.update({
        "is_resolved": True,
        "resolved_at": datetime.utcnow()
    })
    db.commit()
    
    return {"resolved_count": count}
