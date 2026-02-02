"""
Pydantic Schemas for API Request/Response Validation.
Provides data validation and serialization for all endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, IPvAnyAddress
from enum import Enum


# ============== Enums ==============

class DeviceStatus(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class DeviceType(str, Enum):
    ROUTER = "ROUTER"
    SWITCH = "SWITCH"
    SERVER = "SERVER"
    ACCESS_POINT = "ACCESS_POINT"
    FIREWALL = "FIREWALL"
    OTHER = "OTHER"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


# ============== Device Schemas ==============

class DeviceBase(BaseModel):
    """Base schema for device data."""
    ip_address: str = Field(..., description="Device IP address")
    hostname: Optional[str] = Field(None, max_length=255)
    device_type: DeviceType = DeviceType.OTHER
    description: Optional[str] = None
    snmp_community: str = Field("public", max_length=64)
    snmp_port: int = Field(161, ge=1, le=65535)
    is_active: bool = True


class DeviceCreate(DeviceBase):
    """Schema for creating a new device."""
    pass


class DeviceUpdate(BaseModel):
    """Schema for updating a device (all fields optional)."""
    hostname: Optional[str] = None
    device_type: Optional[DeviceType] = None
    description: Optional[str] = None
    snmp_community: Optional[str] = None
    snmp_port: Optional[int] = None
    is_active: Optional[bool] = None


class DeviceResponse(DeviceBase):
    """Schema for device in API responses."""
    id: int
    status: DeviceStatus
    last_seen: Optional[datetime]
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DeviceWithMetrics(DeviceResponse):
    """Device with latest metrics."""
    latest_latency_ms: Optional[float] = None
    latest_packet_loss: Optional[float] = None
    latest_cpu_usage: Optional[float] = None
    # Enhanced discovery fields
    mac_address: Optional[str] = None
    vendor: Optional[str] = None
    os_type: Optional[str] = None
    open_ports: Optional[str] = None  # JSON string


# ============== Metric Schemas ==============

class MetricBase(BaseModel):
    """Base schema for metrics."""
    latency_ms: Optional[float] = None
    packet_loss_percent: Optional[float] = None
    packets_sent: Optional[int] = None
    packets_received: Optional[int] = None
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    uptime_seconds: Optional[int] = None


class MetricCreate(MetricBase):
    """Schema for creating metrics."""
    device_id: int


class MetricResponse(MetricBase):
    """Schema for metrics in API responses."""
    id: int
    device_id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True


# ============== Alert Schemas ==============

class AlertBase(BaseModel):
    """Base schema for alerts."""
    severity: AlertSeverity
    title: str = Field(..., max_length=255)
    message: Optional[str] = None
    metric_type: Optional[str] = None
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None


class AlertCreate(AlertBase):
    """Schema for creating alerts."""
    device_id: int


class AlertResponse(AlertBase):
    """Schema for alerts in API responses."""
    id: int
    device_id: int
    is_resolved: bool
    resolved_at: Optional[datetime]
    created_at: datetime
    
    # Include device IP for convenience
    device_ip: Optional[str] = None
    
    class Config:
        from_attributes = True


class AlertResolve(BaseModel):
    """Schema for resolving an alert."""
    is_resolved: bool = True


# ============== Scan Schemas ==============

class ScanRequest(BaseModel):
    """Schema for triggering a network scan."""
    subnet: str = Field(..., description="Subnet to scan (e.g., 192.168.1.0/24)")
    add_discovered: bool = Field(True, description="Add discovered devices to monitoring")


class ScanLogResponse(BaseModel):
    """Schema for scan log entries."""
    id: int
    timestamp: datetime
    action: str
    details: Optional[str]
    devices_scanned: Optional[int]
    devices_up: Optional[int]
    devices_down: Optional[int]
    duration_seconds: Optional[float]
    success: bool
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


# ============== Dashboard Schemas ==============

class DashboardSummary(BaseModel):
    """Summary statistics for the dashboard."""
    total_devices: int
    devices_up: int
    devices_down: int
    devices_degraded: int
    devices_unknown: int
    active_alerts: int
    critical_alerts: int
    warning_alerts: int
    last_scan: Optional[datetime]


class HealthStatus(BaseModel):
    """API health check response."""
    status: str = "healthy"
    version: str
    timestamp: datetime
    database: str = "connected"


# ============== Device Discovery Schemas ==============

class DeviceDiscoveryRequest(BaseModel):
    """Request to discover device details from IP."""
    ip_address: str = Field(..., description="IP address to discover")
    full_scan: bool = Field(True, description="Include port scanning (slower)")


class DeviceDiscoveryResponse(BaseModel):
    """Response with discovered device details."""
    ip_address: str
    mac_address: Optional[str] = None
    vendor: Optional[str] = None
    os_type: Optional[str] = None
    os_confidence: int = 0
    hostname: Optional[str] = None
    netbios_name: Optional[str] = None
    open_ports: List[dict] = []
    ttl: Optional[int] = None
    discovery_time_seconds: float = 0.0


# ============== Notification Schemas ==============

class NotificationConfigRequest(BaseModel):
    """Configuration for notification channels."""
    smtp_enabled: bool = False
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_to: List[str] = []
    
    webhook_slack_url: Optional[str] = None
    webhook_discord_url: Optional[str] = None
    webhook_teams_url: Optional[str] = None
    
    sound_enabled: bool = True


class TestNotificationRequest(BaseModel):
    """Request to send a test notification."""
    channel: str = Field(..., description="Channel to test: email, slack, discord, teams")
    message: str = Field("Test notification from Mini NOC", description="Test message")

