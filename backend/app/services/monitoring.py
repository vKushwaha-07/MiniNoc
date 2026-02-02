"""
Monitoring Orchestrator - Coordinates all monitoring activities.
Runs periodic health checks, collects metrics, and triggers alerts.
FIXED: Proper hostname resolution, per-device timestamps, metrics storage.
"""

import asyncio
import socket
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.orm import Session

from ..core import settings, main_logger, scan_logger
from ..db.models import Device, Metric, ScanLog, DeviceStatus
from ..db.session import get_db_context
from .icmp_scanner import icmp_scanner, PingResult
from .snmp_poller import snmp_poller
from .alert_engine import alert_engine


def resolve_hostname(ip_address: str) -> Optional[str]:
    """
    Resolve hostname for an IP address using reverse DNS lookup.
    Returns None if resolution fails.
    """
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        return hostname
    except (socket.herror, socket.gaierror, OSError):
        return None


class MonitoringOrchestrator:
    """
    Central orchestrator for all monitoring operations.
    Coordinates ICMP health checks, SNMP polling, and alert generation.
    """
    
    def __init__(self):
        self.is_running = False
        self.scan_interval = settings.SCAN_INTERVAL_SECONDS
        self._task: Optional[asyncio.Task] = None
    
    def _update_device_from_ping(
        self,
        db: Session,
        device: Device,
        ping_result: PingResult
    ) -> Device:
        """
        Update device status and record metrics from ping result.
        Industry-grade: Each device gets its own timestamp.
        """
        now = datetime.utcnow()
        
        if ping_result.is_reachable:
            device.status = DeviceStatus.UP
            device.last_seen = now
            device.consecutive_failures = 0
            
            # Check for degraded status based on thresholds
            if ping_result.packet_loss_percent and ping_result.packet_loss_percent >= settings.PACKET_LOSS_WARNING_PERCENT:
                device.status = DeviceStatus.DEGRADED
            elif ping_result.latency_ms and ping_result.latency_ms >= settings.LATENCY_WARNING_MS:
                device.status = DeviceStatus.DEGRADED
        else:
            device.consecutive_failures = (device.consecutive_failures or 0) + 1
            
            if device.consecutive_failures >= settings.DOWN_THRESHOLD_COUNT:
                device.status = DeviceStatus.DOWN
            else:
                # Keep previous status until threshold reached
                if device.status == DeviceStatus.UNKNOWN:
                    device.status = DeviceStatus.DOWN
        
        device.updated_at = now
        
        # Record metrics for this check
        metric = Metric(
            device_id=device.id,
            timestamp=now,
            latency_ms=ping_result.latency_ms,
            packet_loss_percent=ping_result.packet_loss_percent,
            packets_sent=ping_result.packets_sent,
            packets_received=ping_result.packets_received
        )
        db.add(metric)
        
        return device
    
    async def run_health_check(self, db: Session) -> dict:
        """
        Run a complete health check on all active devices.
        Returns summary statistics.
        """
        start_time = datetime.utcnow()
        
        # Get all active devices
        devices = db.query(Device).filter(Device.is_active == True).all()
        
        if not devices:
            main_logger.info("No active devices to monitor")
            return {"devices_scanned": 0}
        
        ip_addresses = [d.ip_address for d in devices]
        device_map = {d.ip_address: d for d in devices}
        
        # Run ICMP health checks
        scan_logger.info(f"Starting health check on {len(devices)} devices")
        ping_results = await icmp_scanner.health_check_hosts(ip_addresses)
        
        # Process results
        devices_up = 0
        devices_down = 0
        devices_degraded = 0
        alerts_created = 0
        
        for ping_result in ping_results:
            device = device_map.get(ping_result.ip_address)
            if not device:
                continue
            
            # Update device and record metrics
            self._update_device_from_ping(db, device, ping_result)
            
            # Analyze and generate alerts
            alerts = alert_engine.analyze_ping_result(db, device, ping_result)
            alerts_created += len(alerts)
            
            # Count status
            if device.status == DeviceStatus.UP:
                devices_up += 1
            elif device.status == DeviceStatus.DOWN:
                devices_down += 1
            else:
                devices_degraded += 1
        
        # Run SNMP polling for devices that support it
        snmp_devices = [
            {"ip_address": d.ip_address, "snmp_community": d.snmp_community}
            for d in devices if d.snmp_community
        ]
        
        if snmp_devices:
            snmp_results = await snmp_poller.poll_devices(snmp_devices)
            
            for snmp_result in snmp_results:
                device = device_map.get(snmp_result.ip_address)
                if not device or not snmp_result.success:
                    continue
                
                # Analyze SNMP results
                snmp_alerts = alert_engine.analyze_snmp_result(db, device, snmp_result)
                alerts_created += len(snmp_alerts)
                
                # Update latest metric with SNMP data
                latest_metric = db.query(Metric).filter(
                    Metric.device_id == device.id
                ).order_by(Metric.timestamp.desc()).first()
                
                if latest_metric:
                    latest_metric.cpu_usage_percent = snmp_result.cpu_usage_percent
                    latest_metric.memory_usage_percent = snmp_result.memory_usage_percent
                    latest_metric.uptime_seconds = snmp_result.uptime_seconds
        
        # Log scan completion
        duration = (datetime.utcnow() - start_time).total_seconds()
        scan_log = ScanLog(
            action="HEALTH_CHECK",
            details=f"Health check on {len(devices)} devices",
            devices_scanned=len(devices),
            devices_up=devices_up,
            devices_down=devices_down,
            duration_seconds=duration,
            success=True
        )
        db.add(scan_log)
        db.commit()
        
        scan_logger.info(
            f"Health check complete: {devices_up} UP, {devices_down} DOWN, "
            f"{devices_degraded} DEGRADED, {alerts_created} alerts in {duration:.2f}s"
        )
        
        return {
            "devices_scanned": len(devices),
            "devices_up": devices_up,
            "devices_down": devices_down,
            "devices_degraded": devices_degraded,
            "alerts_created": alerts_created,
            "duration_seconds": duration
        }
    
    async def discover_subnet(
        self,
        subnet: str,
        add_discovered: bool = True,
        resolve_hostnames: bool = True
    ) -> dict:
        """
        Discover devices in a subnet and optionally add them to monitoring.
        FIXED: Now resolves hostnames, saves metrics, handles unreachable properly.
        """
        scan_logger.info(f"Starting subnet discovery: {subnet}")
        results, duration = await icmp_scanner.scan_subnet(subnet)
        
        discovered_devices = []
        updated_devices = []
        unreachable_count = 0
        
        with get_db_context() as db:
            for result in results:
                now = datetime.utcnow()
                
                # Check if device already exists
                existing = db.query(Device).filter(
                    Device.ip_address == result.ip_address
                ).first()
                
                if result.is_reachable:
                    # Resolve hostname if enabled
                    hostname = None
                    if resolve_hostnames:
                        hostname = resolve_hostname(result.ip_address)
                    
                    if not existing and add_discovered:
                        # Create new device
                        device = Device(
                            ip_address=result.ip_address,
                            hostname=hostname,
                            status=DeviceStatus.UP,
                            last_seen=now,
                            consecutive_failures=0,
                            created_at=now,
                            updated_at=now
                        )
                        
                        # Determine if degraded based on thresholds
                        if result.packet_loss_percent and result.packet_loss_percent >= settings.PACKET_LOSS_WARNING_PERCENT:
                            device.status = DeviceStatus.DEGRADED
                        elif result.latency_ms and result.latency_ms >= settings.LATENCY_WARNING_MS:
                            device.status = DeviceStatus.DEGRADED
                        
                        db.add(device)
                        db.flush()  # Get the device ID
                        
                        # Save initial metrics
                        metric = Metric(
                            device_id=device.id,
                            timestamp=now,
                            latency_ms=result.latency_ms,
                            packet_loss_percent=result.packet_loss_percent,
                            packets_sent=result.packets_sent,
                            packets_received=result.packets_received
                        )
                        db.add(metric)
                        
                        discovered_devices.append(result.ip_address)
                        scan_logger.info(
                            f"NEW: {result.ip_address} ({hostname or 'no hostname'}) "
                            f"latency={result.latency_ms:.1f}ms loss={result.packet_loss_percent:.0f}%"
                        )
                    
                    elif existing:
                        # Update existing device
                        existing.status = DeviceStatus.UP
                        existing.last_seen = now
                        existing.consecutive_failures = 0
                        existing.updated_at = now
                        
                        # Update hostname if not set
                        if not existing.hostname and hostname:
                            existing.hostname = hostname
                        
                        # Check for degraded
                        if result.packet_loss_percent and result.packet_loss_percent >= settings.PACKET_LOSS_WARNING_PERCENT:
                            existing.status = DeviceStatus.DEGRADED
                        elif result.latency_ms and result.latency_ms >= settings.LATENCY_WARNING_MS:
                            existing.status = DeviceStatus.DEGRADED
                        
                        # Save metrics
                        metric = Metric(
                            device_id=existing.id,
                            timestamp=now,
                            latency_ms=result.latency_ms,
                            packet_loss_percent=result.packet_loss_percent,
                            packets_sent=result.packets_sent,
                            packets_received=result.packets_received
                        )
                        db.add(metric)
                        updated_devices.append(result.ip_address)
                else:
                    # NOT reachable
                    unreachable_count += 1
                    
                    if existing:
                        # Update failure count for existing device
                        existing.consecutive_failures = (existing.consecutive_failures or 0) + 1
                        existing.updated_at = now
                        
                        if existing.consecutive_failures >= settings.DEVICE_DOWN_THRESHOLD:
                            existing.status = DeviceStatus.DOWN
                            scan_logger.warning(
                                f"DOWN: {result.ip_address} (failures: {existing.consecutive_failures})"
                            )
            
            # Log discovery
            reachable_count = sum(1 for r in results if r.is_reachable)
            scan_log = ScanLog(
                action="DISCOVERY",
                details=f"Subnet scan: {subnet} - {len(discovered_devices)} new, {len(updated_devices)} updated",
                devices_scanned=len(results),
                devices_up=reachable_count,
                devices_down=unreachable_count,
                duration_seconds=duration,
                success=True
            )
            db.add(scan_log)
            db.commit()
        
        scan_logger.info(
            f"Discovery complete: {len(discovered_devices)} new, "
            f"{len(updated_devices)} updated, {unreachable_count} unreachable"
        )
        
        return {
            "subnet": subnet,
            "total_hosts": len(results),
            "reachable_hosts": sum(1 for r in results if r.is_reachable),
            "unreachable_hosts": unreachable_count,
            "new_devices_added": len(discovered_devices),
            "existing_devices_updated": len(updated_devices),
            "duration_seconds": duration
        }
    
    async def _monitoring_loop(self):
        """Background loop for periodic monitoring."""
        main_logger.info(f"Monitoring loop started (interval: {self.scan_interval}s)")
        
        while self.is_running:
            try:
                with get_db_context() as db:
                    await self.run_health_check(db)
            except Exception as e:
                main_logger.error(f"Health check failed: {e}")
            
            await asyncio.sleep(self.scan_interval)
    
    def start_background_monitoring(self):
        """Start the background monitoring task."""
        if self.is_running:
            main_logger.warning("Monitoring already running")
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._monitoring_loop())
        main_logger.info("Background monitoring started")
    
    def stop_background_monitoring(self):
        """Stop the background monitoring task."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None
        main_logger.info("Background monitoring stopped")


# Singleton instance
monitoring_orchestrator = MonitoringOrchestrator()
