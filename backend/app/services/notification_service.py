"""
Notification Service - Multi-channel alert notifications.
Supports Email (SMTP), Webhooks (Slack, Discord, Teams), and browser notifications.
Industry-grade notification system for NOC alerting.
"""

import asyncio
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import aiohttp

from ..core import main_logger, settings


@dataclass
class NotificationConfig:
    """Configuration for notification channels."""
    # Email (SMTP)
    smtp_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_to: List[str] = None
    
    # Webhooks
    webhook_slack_url: str = ""
    webhook_discord_url: str = ""
    webhook_teams_url: str = ""
    webhook_custom_url: str = ""
    
    # Sound alerts
    sound_enabled: bool = True
    sound_critical: str = "alert_critical.mp3"
    sound_warning: str = "alert_warning.mp3"


@dataclass
class NotificationPayload:
    """Payload for sending notifications."""
    title: str
    message: str
    severity: str  # CRITICAL, WARNING, INFO
    device_ip: Optional[str] = None
    device_hostname: Optional[str] = None
    metric_type: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class NotificationService:
    """
    Multi-channel notification service.
    Sends alerts via email, webhooks, and broadcasts to connected clients.
    """
    
    def __init__(self, config: NotificationConfig = None):
        self.config = config or NotificationConfig()
        self._websocket_clients = set()  # For real-time browser notifications
        
    def set_config(self, config: NotificationConfig):
        """Update notification configuration."""
        self.config = config
        main_logger.info("Notification config updated")
    
    # ==================== EMAIL ====================
    
    async def send_email(self, payload: NotificationPayload) -> bool:
        """
        Send alert notification via email (SMTP).
        """
        if not self.config.smtp_enabled:
            return False
        
        try:
            # Build email content
            subject = f"[{payload.severity}] {payload.title}"
            
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .alert-box {{ padding: 20px; border-radius: 5px; margin: 10px 0; }}
                    .critical {{ background-color: #fee; border-left: 4px solid #c00; }}
                    .warning {{ background-color: #fff3cd; border-left: 4px solid #ffc107; }}
                    .info {{ background-color: #e7f3ff; border-left: 4px solid #0d6efd; }}
                    .details {{ margin-top: 15px; }}
                    .label {{ color: #666; font-size: 12px; }}
                    .value {{ font-weight: bold; }}
                </style>
            </head>
            <body>
                <h2>🔔 Mini NOC Alert</h2>
                <div class="alert-box {payload.severity.lower()}">
                    <h3>{payload.title}</h3>
                    <p>{payload.message}</p>
                </div>
                <div class="details">
                    <p><span class="label">Device:</span> 
                       <span class="value">{payload.device_ip or 'N/A'} 
                       ({payload.device_hostname or 'Unknown'})</span></p>
                    <p><span class="label">Severity:</span> 
                       <span class="value">{payload.severity}</span></p>
                    <p><span class="label">Time:</span> 
                       <span class="value">{payload.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</span></p>
                    {f'<p><span class="label">Metric:</span> <span class="value">{payload.metric_type}: {payload.metric_value} (threshold: {payload.threshold})</span></p>' if payload.metric_type else ''}
                </div>
                <hr>
                <p style="color: #888; font-size: 11px;">
                    This alert was sent by Mini NOC - Network Monitoring System
                </p>
            </body>
            </html>
            """
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.config.smtp_from
            msg["To"] = ", ".join(self.config.smtp_to or [])
            
            msg.attach(MIMEText(payload.message, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            
            # Send in thread pool (blocking operation)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_email_sync, msg)
            
            main_logger.info(f"Email sent: {subject}")
            return True
            
        except Exception as e:
            main_logger.error(f"Failed to send email: {e}")
            return False
    
    def _send_email_sync(self, msg):
        """Synchronous email sending."""
        with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
            server.starttls()
            server.login(self.config.smtp_user, self.config.smtp_password)
            server.send_message(msg)
    
    # ==================== WEBHOOKS ====================
    
    async def send_webhook_slack(self, payload: NotificationPayload) -> bool:
        """Send notification to Slack webhook."""
        if not self.config.webhook_slack_url:
            return False
        
        color = {"CRITICAL": "#dc3545", "WARNING": "#ffc107", "INFO": "#17a2b8"}.get(payload.severity, "#6c757d")
        
        slack_payload = {
            "attachments": [{
                "color": color,
                "title": f"🔔 {payload.title}",
                "text": payload.message,
                "fields": [
                    {"title": "Device", "value": f"{payload.device_ip} ({payload.device_hostname or 'Unknown'})", "short": True},
                    {"title": "Severity", "value": payload.severity, "short": True},
                ],
                "footer": "Mini NOC",
                "ts": int(payload.timestamp.timestamp())
            }]
        }
        
        if payload.metric_type:
            slack_payload["attachments"][0]["fields"].append({
                "title": payload.metric_type,
                "value": f"{payload.metric_value} (threshold: {payload.threshold})",
                "short": True
            })
        
        return await self._send_webhook(self.config.webhook_slack_url, slack_payload)
    
    async def send_webhook_discord(self, payload: NotificationPayload) -> bool:
        """Send notification to Discord webhook."""
        if not self.config.webhook_discord_url:
            return False
        
        color = {"CRITICAL": 0xdc3545, "WARNING": 0xffc107, "INFO": 0x17a2b8}.get(payload.severity, 0x6c757d)
        
        discord_payload = {
            "embeds": [{
                "title": f"🔔 {payload.title}",
                "description": payload.message,
                "color": color,
                "fields": [
                    {"name": "Device", "value": f"{payload.device_ip}", "inline": True},
                    {"name": "Severity", "value": payload.severity, "inline": True},
                ],
                "footer": {"text": "Mini NOC"},
                "timestamp": payload.timestamp.isoformat()
            }]
        }
        
        return await self._send_webhook(self.config.webhook_discord_url, discord_payload)
    
    async def send_webhook_teams(self, payload: NotificationPayload) -> bool:
        """Send notification to Microsoft Teams webhook."""
        if not self.config.webhook_teams_url:
            return False
        
        color = {"CRITICAL": "dc3545", "WARNING": "ffc107", "INFO": "17a2b8"}.get(payload.severity, "6c757d")
        
        teams_payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color,
            "summary": payload.title,
            "sections": [{
                "activityTitle": f"🔔 {payload.title}",
                "activitySubtitle": payload.message,
                "facts": [
                    {"name": "Device", "value": f"{payload.device_ip} ({payload.device_hostname or 'Unknown'})"},
                    {"name": "Severity", "value": payload.severity},
                    {"name": "Time", "value": payload.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')},
                ],
                "markdown": True
            }]
        }
        
        return await self._send_webhook(self.config.webhook_teams_url, teams_payload)
    
    async def _send_webhook(self, url: str, payload: dict) -> bool:
        """Generic webhook sender."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    success = response.status in (200, 201, 204)
                    if success:
                        main_logger.info(f"Webhook sent to {url[:50]}...")
                    else:
                        main_logger.warning(f"Webhook failed: {response.status}")
                    return success
        except Exception as e:
            main_logger.error(f"Webhook error: {e}")
            return False
    
    # ==================== BROADCAST ====================
    
    async def notify_all(self, payload: NotificationPayload) -> Dict[str, bool]:
        """
        Send notification through all configured channels.
        Returns dict of channel -> success status.
        """
        results = {}
        
        # Parallel execution of all channels
        tasks = []
        
        if self.config.smtp_enabled:
            tasks.append(("email", self.send_email(payload)))
        
        if self.config.webhook_slack_url:
            tasks.append(("slack", self.send_webhook_slack(payload)))
        
        if self.config.webhook_discord_url:
            tasks.append(("discord", self.send_webhook_discord(payload)))
        
        if self.config.webhook_teams_url:
            tasks.append(("teams", self.send_webhook_teams(payload)))
        
        # Execute all tasks
        for channel, task in tasks:
            try:
                results[channel] = await task
            except Exception as e:
                main_logger.error(f"Notification failed for {channel}: {e}")
                results[channel] = False
        
        return results
    
    def create_alert_payload(
        self,
        title: str,
        message: str,
        severity: str,
        device_ip: str = None,
        device_hostname: str = None,
        metric_type: str = None,
        metric_value: float = None,
        threshold: float = None
    ) -> NotificationPayload:
        """Helper to create notification payload."""
        return NotificationPayload(
            title=title,
            message=message,
            severity=severity,
            device_ip=device_ip,
            device_hostname=device_hostname,
            metric_type=metric_type,
            metric_value=metric_value,
            threshold=threshold
        )


# Singleton instance with default config
notification_service = NotificationService()
