"""
Incident Management API Routes.
Endpoints for creating, managing, and resolving incidents.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db.session import get_db
from ..db.models import (
    Incident, IncidentUpdate, IncidentAlert, Alert,
    IncidentStatus, IncidentPriority
)

router = APIRouter()


# ============================================
# SCHEMAS
# ============================================

class IncidentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "P3"
    affected_devices: Optional[str] = None  # JSON array
    impact_summary: Optional[str] = None
    created_by: Optional[str] = None

class IncidentUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    impact_summary: Optional[str] = None
    root_cause: Optional[str] = None
    resolution: Optional[str] = None
    assigned_to: Optional[str] = None

class IncidentTimelineEntry(BaseModel):
    message: str
    update_type: str = "update"
    created_by: Optional[str] = None

class LinkAlertRequest(BaseModel):
    alert_ids: List[int]

class IncidentResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    priority: str
    affected_devices: Optional[str]
    impact_summary: Optional[str]
    root_cause: Optional[str]
    resolution: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    created_by: Optional[str]
    assigned_to: Optional[str]
    updates_count: int = 0
    linked_alerts_count: int = 0
    
    class Config:
        from_attributes = True

class TimelineResponse(BaseModel):
    id: int
    message: str
    update_type: str
    previous_status: Optional[str]
    new_status: Optional[str]
    created_at: datetime
    created_by: Optional[str]
    
    class Config:
        from_attributes = True


# ============================================
# ENDPOINTS
# ============================================

@router.get("/", response_model=List[IncidentResponse])
def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List all incidents with optional filtering."""
    query = db.query(Incident)
    
    if status:
        query = query.filter(Incident.status == status)
    if priority:
        query = query.filter(Incident.priority == priority)
    
    incidents = query.order_by(Incident.created_at.desc()).limit(limit).all()
    
    result = []
    for inc in incidents:
        result.append(IncidentResponse(
            id=inc.id,
            title=inc.title,
            description=inc.description,
            status=inc.status.value if inc.status else "OPEN",
            priority=inc.priority.value if inc.priority else "P3",
            affected_devices=inc.affected_devices,
            impact_summary=inc.impact_summary,
            root_cause=inc.root_cause,
            resolution=inc.resolution,
            created_at=inc.created_at,
            updated_at=inc.updated_at,
            resolved_at=inc.resolved_at,
            created_by=inc.created_by,
            assigned_to=inc.assigned_to,
            updates_count=len(inc.updates),
            linked_alerts_count=len(inc.linked_alerts)
        ))
    
    return result


@router.post("/", response_model=IncidentResponse)
def create_incident(
    request: IncidentCreate,
    db: Session = Depends(get_db)
):
    """Create a new incident."""
    incident = Incident(
        title=request.title,
        description=request.description,
        priority=IncidentPriority(request.priority) if request.priority in ["P1", "P2", "P3", "P4"] else IncidentPriority.P3,
        affected_devices=request.affected_devices,
        impact_summary=request.impact_summary,
        created_by=request.created_by,
        status=IncidentStatus.OPEN
    )
    
    db.add(incident)
    db.commit()
    db.refresh(incident)
    
    # Add initial timeline entry
    initial_update = IncidentUpdate(
        incident_id=incident.id,
        message="Incident created",
        update_type="created",
        new_status="OPEN",
        created_by=request.created_by
    )
    db.add(initial_update)
    db.commit()
    
    return IncidentResponse(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        status=incident.status.value,
        priority=incident.priority.value,
        affected_devices=incident.affected_devices,
        impact_summary=incident.impact_summary,
        root_cause=incident.root_cause,
        resolution=incident.resolution,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        created_by=incident.created_by,
        assigned_to=incident.assigned_to,
        updates_count=1,
        linked_alerts_count=0
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db)
):
    """Get incident details by ID."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return IncidentResponse(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        status=incident.status.value if incident.status else "OPEN",
        priority=incident.priority.value if incident.priority else "P3",
        affected_devices=incident.affected_devices,
        impact_summary=incident.impact_summary,
        root_cause=incident.root_cause,
        resolution=incident.resolution,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        created_by=incident.created_by,
        assigned_to=incident.assigned_to,
        updates_count=len(incident.updates),
        linked_alerts_count=len(incident.linked_alerts)
    )


@router.patch("/{incident_id}", response_model=IncidentResponse)
def update_incident(
    incident_id: int,
    request: IncidentUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update incident details and status."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    old_status = incident.status.value if incident.status else "OPEN"
    
    # Update fields if provided
    if request.title:
        incident.title = request.title
    if request.description:
        incident.description = request.description
    if request.priority:
        incident.priority = IncidentPriority(request.priority)
    if request.impact_summary:
        incident.impact_summary = request.impact_summary
    if request.root_cause:
        incident.root_cause = request.root_cause
    if request.resolution:
        incident.resolution = request.resolution
    if request.assigned_to:
        incident.assigned_to = request.assigned_to
    
    # Handle status change
    if request.status:
        new_status = IncidentStatus(request.status)
        incident.status = new_status
        
        if new_status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.utcnow()
        
        # Log status change
        update = IncidentUpdate(
            incident_id=incident.id,
            message=f"Status changed from {old_status} to {request.status}",
            update_type="status_change",
            previous_status=old_status,
            new_status=request.status
        )
        db.add(update)
    
    incident.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(incident)
    
    return IncidentResponse(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        status=incident.status.value,
        priority=incident.priority.value,
        affected_devices=incident.affected_devices,
        impact_summary=incident.impact_summary,
        root_cause=incident.root_cause,
        resolution=incident.resolution,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        created_by=incident.created_by,
        assigned_to=incident.assigned_to,
        updates_count=len(incident.updates),
        linked_alerts_count=len(incident.linked_alerts)
    )


@router.get("/{incident_id}/timeline", response_model=List[TimelineResponse])
def get_incident_timeline(
    incident_id: int,
    db: Session = Depends(get_db)
):
    """Get incident timeline/updates history."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    updates = db.query(IncidentUpdate).filter(
        IncidentUpdate.incident_id == incident_id
    ).order_by(IncidentUpdate.created_at.desc()).all()
    
    return [TimelineResponse(
        id=u.id,
        message=u.message,
        update_type=u.update_type,
        previous_status=u.previous_status,
        new_status=u.new_status,
        created_at=u.created_at,
        created_by=u.created_by
    ) for u in updates]


@router.post("/{incident_id}/timeline")
def add_timeline_entry(
    incident_id: int,
    entry: IncidentTimelineEntry,
    db: Session = Depends(get_db)
):
    """Add a new timeline entry to an incident."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    update = IncidentUpdate(
        incident_id=incident_id,
        message=entry.message,
        update_type=entry.update_type,
        created_by=entry.created_by
    )
    
    db.add(update)
    incident.updated_at = datetime.utcnow()
    db.commit()
    
    return {"status": "success", "message": "Timeline entry added"}


@router.post("/{incident_id}/link-alerts")
def link_alerts_to_incident(
    incident_id: int,
    request: LinkAlertRequest,
    db: Session = Depends(get_db)
):
    """Link alerts to an incident."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    linked_count = 0
    for alert_id in request.alert_ids:
        # Check if alert exists
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            continue
        
        # Check if already linked
        existing = db.query(IncidentAlert).filter(
            IncidentAlert.incident_id == incident_id,
            IncidentAlert.alert_id == alert_id
        ).first()
        
        if not existing:
            link = IncidentAlert(
                incident_id=incident_id,
                alert_id=alert_id
            )
            db.add(link)
            linked_count += 1
    
    if linked_count > 0:
        update = IncidentUpdate(
            incident_id=incident_id,
            message=f"Linked {linked_count} alert(s) to this incident",
            update_type="alert_linked"
        )
        db.add(update)
        incident.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "status": "success",
        "linked_count": linked_count,
        "total_linked": len(incident.linked_alerts)
    }


@router.delete("/{incident_id}")
def delete_incident(
    incident_id: int,
    db: Session = Depends(get_db)
):
    """Delete an incident."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    db.delete(incident)
    db.commit()
    
    return {"status": "success", "message": f"Incident {incident_id} deleted"}
