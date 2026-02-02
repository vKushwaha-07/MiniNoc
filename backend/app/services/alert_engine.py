"""
Alert Engine for Fault Detection and Notification.
Analyzes metrics against thresholds and generates alerts.
"""

from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from ..core import settings, alert_logger
from ..db.models import Device, Metric, Alert, DeviceStatus, AlertSeverity
from .icmp_scanner import PingResult
from .snmp_poller import SNMPResult


class AlertEngine:
    """
    Fault detection engine that analyzes metrics and generates alerts.
    Implements threshold-based alerting for latency, packet loss, and CPU.
    """
    
    def __init__(self):
        # Load thresholds from settings
        self.packet_loss_warning = settings.PACKET_LOSS_WARNING_PERCENT
        self.packet_loss_critical = settings.PACKET_LOSS_CRITICAL_PERCENT
        self.latency_warning = settings.LATENCY_WARNING_MS
        self.latency_critical = settings.LATENCY_CRITICAL_MS
        self.cpu_warning = settings.CPU_WARNING_PERCENT
        self.cpu_critical = settings.CPU_CRITICAL_PERCENT
        self.down_threshold = settings.DOWN_THRESHOLD_COUNT
    
    def analyze_ping_result(
        self,
        db: Session,
        device: Device,
        ping_result: PingResult
    ) -> List[Alert]:
        """
        Analyze ping result and generate appropriate alerts.
        
        Returns list of new alerts created.
        """
        alerts = []
        now = datetime.utcnow()
        
        # Check device status change
        previous_status = device.status
        
        if ping_result.is_reachable:
            # Device is up - reset failure counter
            device.consecutive_failures = 0
            device.last_seen = now
            
            # Check for status recovery
            if previous_status == DeviceStatus.DOWN:
                device.status = DeviceStatus.UP
                alert = self._create_recovery_alert(db, device, "Device recovered - now responding to ICMP")
                alerts.append(alert)
            else:
                # Check if degraded due to packet loss
                if ping_result.packet_loss_percent >= self.packet_loss_warning:
                    device.status = DeviceStatus.DEGRADED
                else:
                    device.status = DeviceStatus.UP
            
            # Check latency thresholds
            if ping_result.latency_ms:
                latency_alert = self._check_latency(db, device, ping_result.latency_ms)
                if latency_alert:
                    alerts.append(latency_alert)
            
            # Check packet loss thresholds
            if ping_result.packet_loss_percent > 0:
                loss_alert = self._check_packet_loss(db, device, ping_result.packet_loss_percent)
                if loss_alert:
                    alerts.append(loss_alert)
        else:
            # Device is not responding
            device.consecutive_failures += 1
            
            if device.consecutive_failures >= self.down_threshold:
                if previous_status != DeviceStatus.DOWN:
                    device.status = DeviceStatus.DOWN
                    alert = self._create_down_alert(db, device)
                    alerts.append(alert)
        
        return alerts
    
    def analyze_snmp_result(
        self,
        db: Session,
        device: Device,
        snmp_result: SNMPResult
    ) -> List[Alert]:
        """
        Analyze SNMP result and generate alerts for CPU/memory issues.
        """
        alerts = []
        
        if not snmp_result.success:
            return alerts
        
        # Check CPU usage
        if snmp_result.cpu_usage_percent is not None:
            cpu_alert = self._check_cpu_usage(db, device, snmp_result.cpu_usage_percent)
            if cpu_alert:
                alerts.append(cpu_alert)
        
        # Check memory usage (if we add thresholds later)
        # Currently just logging for awareness
        if snmp_result.memory_usage_percent is not None and snmp_result.memory_usage_percent > 90:
            alert_logger.warning(
                f"High memory usage on {device.ip_address}: {snmp_result.memory_usage_percent:.1f}%"
            )
        
        return alerts
    
    def _check_latency(
        self,
        db: Session,
        device: Device,
        latency_ms: float
    ) -> Optional[Alert]:
        """Check latency against thresholds and create alert if needed."""
        
        if latency_ms >= self.latency_critical:
            severity = AlertSeverity.CRITICAL
            title = f"Critical latency: {latency_ms:.1f}ms"
        elif latency_ms >= self.latency_warning:
            severity = AlertSeverity.WARNING
            title = f"High latency: {latency_ms:.1f}ms"
        else:
            return None
        
        # Check for existing unresolved alert
        existing = db.query(Alert).filter(
            Alert.device_id == device.id,
            Alert.metric_type == "latency",
            Alert.is_resolved == False
        ).first()
        
        if existing:
            return None  # Don't duplicate
        
        alert = Alert(
            device_id=device.id,
            severity=severity,
            title=title,
            message=f"Latency exceeded threshold ({self.latency_warning}ms warning, {self.latency_critical}ms critical)",
            metric_type="latency",
            metric_value=latency_ms,
            threshold_value=self.latency_warning if severity == AlertSeverity.WARNING else self.latency_critical
        )
        
        db.add(alert)
        alert_logger.warning(f"[{severity}] {device.ip_address}: {title}")
        return alert
    
    def _check_packet_loss(
        self,
        db: Session,
        device: Device,
        packet_loss_percent: float
    ) -> Optional[Alert]:
        """Check packet loss against thresholds."""
        
        if packet_loss_percent >= self.packet_loss_critical:
            severity = AlertSeverity.CRITICAL
            title = f"Critical packet loss: {packet_loss_percent:.1f}%"
        elif packet_loss_percent >= self.packet_loss_warning:
            severity = AlertSeverity.WARNING
            title = f"Packet loss detected: {packet_loss_percent:.1f}%"
        else:
            return None
        
        existing = db.query(Alert).filter(
            Alert.device_id == device.id,
            Alert.metric_type == "packet_loss",
            Alert.is_resolved == False
        ).first()
        
        if existing:
            return None
        
        alert = Alert(
            device_id=device.id,
            severity=severity,
            title=title,
            message=f"Packet loss exceeded threshold",
            metric_type="packet_loss",
            metric_value=packet_loss_percent,
            threshold_value=self.packet_loss_warning if severity == AlertSeverity.WARNING else self.packet_loss_critical
        )
        
        db.add(alert)
        alert_logger.warning(f"[{severity}] {device.ip_address}: {title}")
        return alert
    
    def _check_cpu_usage(
        self,
        db: Session,
        device: Device,
        cpu_percent: float
    ) -> Optional[Alert]:
        """Check CPU usage against thresholds."""
        
        if cpu_percent >= self.cpu_critical:
            severity = AlertSeverity.CRITICAL
            title = f"Critical CPU usage: {cpu_percent:.1f}%"
        elif cpu_percent >= self.cpu_warning:
            severity = AlertSeverity.WARNING
            title = f"High CPU usage: {cpu_percent:.1f}%"
        else:
            return None
        
        existing = db.query(Alert).filter(
            Alert.device_id == device.id,
            Alert.metric_type == "cpu",
            Alert.is_resolved == False
        ).first()
        
        if existing:
            return None
        
        alert = Alert(
            device_id=device.id,
            severity=severity,
            title=title,
            message=f"CPU usage exceeded threshold",
            metric_type="cpu",
            metric_value=cpu_percent,
            threshold_value=self.cpu_warning if severity == AlertSeverity.WARNING else self.cpu_critical
        )
        
        db.add(alert)
        alert_logger.warning(f"[{severity}] {device.ip_address}: {title}")
        return alert
    
    def _create_down_alert(self, db: Session, device: Device) -> Alert:
        """Create alert for device going DOWN."""
        alert = Alert(
            device_id=device.id,
            severity=AlertSeverity.CRITICAL,
            title="Device DOWN",
            message=f"Device failed to respond after {self.down_threshold} consecutive checks",
            metric_type="availability"
        )
        db.add(alert)
        alert_logger.critical(f"[CRITICAL] {device.ip_address}: Device DOWN")
        return alert
    
    def _create_recovery_alert(self, db: Session, device: Device, message: str) -> Alert:
        """Create alert for device recovery."""
        # Resolve any existing DOWN alerts
        db.query(Alert).filter(
            Alert.device_id == device.id,
            Alert.metric_type == "availability",
            Alert.is_resolved == False
        ).update({
            "is_resolved": True,
            "resolved_at": datetime.utcnow()
        })
        
        alert = Alert(
            device_id=device.id,
            severity=AlertSeverity.INFO,
            title="Device RECOVERED",
            message=message,
            metric_type="availability"
        )
        db.add(alert)
        alert_logger.info(f"[INFO] {device.ip_address}: Device RECOVERED")
        return alert
    
    def auto_resolve_alerts(self, db: Session, device: Device, metric_type: str) -> int:
        """
        Auto-resolve alerts when metrics return to normal.
        Returns count of resolved alerts.
        """
        now = datetime.utcnow()
        result = db.query(Alert).filter(
            Alert.device_id == device.id,
            Alert.metric_type == metric_type,
            Alert.is_resolved == False
        ).update({
            "is_resolved": True,
            "resolved_at": now
        })
        
        if result > 0:
            alert_logger.info(f"Auto-resolved {result} {metric_type} alert(s) for {device.ip_address}")
        
        return result


# Singleton instance
alert_engine = AlertEngine()
