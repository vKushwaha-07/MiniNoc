"""
Notifications API Routes.
Endpoints for configuring and testing notification channels.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from ..api.schemas import NotificationConfigRequest, TestNotificationRequest
from ..services.notification_service import (
    notification_service, 
    NotificationConfig, 
    NotificationPayload
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# In-memory config storage (in production, use database)
_notification_config: Optional[NotificationConfig] = None


@router.get("/config")
async def get_notification_config():
    """Get current notification configuration (passwords masked)."""
    if not _notification_config:
        return {"configured": False}
    
    return {
        "configured": True,
        "smtp_enabled": _notification_config.smtp_enabled,
        "smtp_host": _notification_config.smtp_host,
        "smtp_port": _notification_config.smtp_port,
        "smtp_user": _notification_config.smtp_user,
        "smtp_from": _notification_config.smtp_from,
        "smtp_to": _notification_config.smtp_to,
        "webhook_slack_configured": bool(_notification_config.webhook_slack_url),
        "webhook_discord_configured": bool(_notification_config.webhook_discord_url),
        "webhook_teams_configured": bool(_notification_config.webhook_teams_url),
        "sound_enabled": _notification_config.sound_enabled
    }


@router.post("/config")
async def update_notification_config(request: NotificationConfigRequest):
    """
    Update notification configuration.
    
    Supports:
    - Email (SMTP) notifications
    - Slack webhooks
    - Discord webhooks  
    - Microsoft Teams webhooks
    - Browser sound alerts
    """
    global _notification_config
    
    _notification_config = NotificationConfig(
        smtp_enabled=request.smtp_enabled,
        smtp_host=request.smtp_host or "",
        smtp_port=request.smtp_port,
        smtp_user=request.smtp_user or "",
        smtp_password=request.smtp_password or "",
        smtp_from=request.smtp_from or "",
        smtp_to=request.smtp_to or [],
        webhook_slack_url=request.webhook_slack_url or "",
        webhook_discord_url=request.webhook_discord_url or "",
        webhook_teams_url=request.webhook_teams_url or "",
        sound_enabled=request.sound_enabled
    )
    
    notification_service.set_config(_notification_config)
    
    return {"message": "Notification configuration updated", "configured": True}


@router.post("/test")
async def test_notification(request: TestNotificationRequest):
    """
    Send a test notification to verify configuration.
    
    Channels: email, slack, discord, teams
    """
    if not _notification_config:
        raise HTTPException(
            status_code=400,
            detail="No notification configuration set. Configure notifications first."
        )
    
    payload = NotificationPayload(
        title="Test Notification",
        message=request.message,
        severity="INFO",
        device_ip="192.168.1.1",
        device_hostname="test-device"
    )
    
    channel = request.channel.lower()
    
    try:
        if channel == "email":
            if not _notification_config.smtp_enabled:
                raise HTTPException(status_code=400, detail="SMTP is not enabled")
            success = await notification_service.send_email(payload)
        elif channel == "slack":
            if not _notification_config.webhook_slack_url:
                raise HTTPException(status_code=400, detail="Slack webhook not configured")
            success = await notification_service.send_webhook_slack(payload)
        elif channel == "discord":
            if not _notification_config.webhook_discord_url:
                raise HTTPException(status_code=400, detail="Discord webhook not configured")
            success = await notification_service.send_webhook_discord(payload)
        elif channel == "teams":
            if not _notification_config.webhook_teams_url:
                raise HTTPException(status_code=400, detail="Teams webhook not configured")
            success = await notification_service.send_webhook_teams(payload)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown channel: {channel}")
        
        if success:
            return {"message": f"Test notification sent to {channel}", "success": True}
        else:
            return {"message": f"Failed to send to {channel}", "success": False}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send")
async def send_notification(
    title: str,
    message: str,
    severity: str = "INFO",
    device_ip: str = None,
    device_hostname: str = None
):
    """
    Send a notification through all configured channels.
    
    Used for manual alerts or integration with external systems.
    """
    if not _notification_config:
        raise HTTPException(
            status_code=400,
            detail="No notification configuration set"
        )
    
    payload = NotificationPayload(
        title=title,
        message=message,
        severity=severity.upper(),
        device_ip=device_ip,
        device_hostname=device_hostname
    )
    
    results = await notification_service.notify_all(payload)
    
    return {
        "message": "Notification sent",
        "channels": results,
        "any_success": any(results.values())
    }
