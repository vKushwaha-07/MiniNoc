"""
SNMP Poller Service for Device Metrics Collection.
Retrieves CPU, memory, and interface statistics via SNMP v2c.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

from ..core import scan_logger, settings

# SNMP library import with fallback
try:
    from pysnmp.hlapi import (
        getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
        ContextData, ObjectType, ObjectIdentity
    )
    SNMP_AVAILABLE = True
except ImportError:
    SNMP_AVAILABLE = False
    scan_logger.warning("pysnmp not available - SNMP polling disabled")


# Common SNMP OIDs
class OID:
    """Standard SNMP OIDs for network monitoring."""
    # System
    SYS_DESCR = "1.3.6.1.2.1.1.1.0"
    SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
    SYS_NAME = "1.3.6.1.2.1.1.5.0"
    
    # CPU (UCD-SNMP-MIB - common on Linux/network devices)
    CPU_LOAD_1MIN = "1.3.6.1.4.1.2021.10.1.3.1"
    CPU_IDLE = "1.3.6.1.4.1.2021.11.11.0"
    
    # Memory (UCD-SNMP-MIB)
    MEM_TOTAL = "1.3.6.1.4.1.2021.4.5.0"
    MEM_AVAIL = "1.3.6.1.4.1.2021.4.6.0"
    MEM_CACHED = "1.3.6.1.4.1.2021.4.15.0"
    
    # Interface (IF-MIB)
    IF_NUMBER = "1.3.6.1.2.1.2.1.0"
    IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
    IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
    IF_IN_OCTETS = "1.3.6.1.2.1.2.2.1.10"
    IF_OUT_OCTETS = "1.3.6.1.2.1.2.2.1.16"


@dataclass
class SNMPResult:
    """Result of SNMP polling operation."""
    ip_address: str
    success: bool
    
    # System Info
    system_name: Optional[str] = None
    system_description: Optional[str] = None
    uptime_seconds: Optional[int] = None
    
    # Performance Metrics
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    
    # Interface Info
    interface_count: Optional[int] = None
    
    # Error handling
    error_message: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class SNMPPoller:
    """
    SNMP v2c poller for retrieving device metrics.
    Supports system info, CPU, memory, and interface statistics.
    """
    
    def __init__(
        self,
        community: str = None,
        port: int = None,
        timeout: float = None
    ):
        self.community = community or settings.SNMP_COMMUNITY
        self.port = port or settings.SNMP_PORT
        self.timeout = timeout or settings.SNMP_TIMEOUT
        
        if not SNMP_AVAILABLE:
            scan_logger.warning("SNMPPoller initialized but pysnmp is not installed")
    
    def _snmp_get(
        self,
        ip_address: str,
        oid: str,
        community: str = None
    ) -> Optional[Any]:
        """
        Perform a single SNMP GET request.
        Returns the value or None on failure.
        """
        if not SNMP_AVAILABLE:
            return None
        
        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community or self.community),
                UdpTransportTarget((ip_address, self.port), timeout=self.timeout),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            
            error_indication, error_status, error_index, var_binds = next(iterator)
            
            if error_indication or error_status:
                return None
            
            for var_bind in var_binds:
                return var_bind[1]
            
            return None
            
        except Exception as e:
            scan_logger.debug(f"SNMP GET failed for {ip_address} OID {oid}: {e}")
            return None
    
    def poll_device(
        self,
        ip_address: str,
        community: str = None
    ) -> SNMPResult:
        """
        Poll a device for all available SNMP metrics.
        Synchronous version for thread pool execution.
        """
        result = SNMPResult(ip_address=ip_address, success=False)
        
        if not SNMP_AVAILABLE:
            result.error_message = "SNMP library not available"
            return result
        
        try:
            raw_data = {}
            
            # System Information
            sys_name = self._snmp_get(ip_address, OID.SYS_NAME, community)
            if sys_name:
                result.system_name = str(sys_name)
                raw_data['sys_name'] = str(sys_name)
            
            sys_descr = self._snmp_get(ip_address, OID.SYS_DESCR, community)
            if sys_descr:
                result.system_description = str(sys_descr)
                raw_data['sys_descr'] = str(sys_descr)
            
            uptime = self._snmp_get(ip_address, OID.SYS_UPTIME, community)
            if uptime:
                # Convert timeticks (1/100th second) to seconds
                result.uptime_seconds = int(uptime) // 100
                raw_data['uptime'] = result.uptime_seconds
            
            # CPU Usage (try to get idle percentage and calculate usage)
            cpu_idle = self._snmp_get(ip_address, OID.CPU_IDLE, community)
            if cpu_idle is not None:
                try:
                    idle_value = float(cpu_idle)
                    result.cpu_usage_percent = 100.0 - idle_value
                    raw_data['cpu_idle'] = idle_value
                except (ValueError, TypeError):
                    pass
            
            # Memory Usage
            mem_total = self._snmp_get(ip_address, OID.MEM_TOTAL, community)
            mem_avail = self._snmp_get(ip_address, OID.MEM_AVAIL, community)
            if mem_total and mem_avail:
                try:
                    total = int(mem_total)
                    avail = int(mem_avail)
                    if total > 0:
                        result.memory_usage_percent = ((total - avail) / total) * 100
                        raw_data['mem_total'] = total
                        raw_data['mem_avail'] = avail
                except (ValueError, TypeError):
                    pass
            
            # Interface Count
            if_count = self._snmp_get(ip_address, OID.IF_NUMBER, community)
            if if_count:
                try:
                    result.interface_count = int(if_count)
                    raw_data['if_count'] = result.interface_count
                except (ValueError, TypeError):
                    pass
            
            # Mark as successful if we got at least system info
            if result.system_name or result.uptime_seconds is not None:
                result.success = True
            
            result.raw_data = raw_data
            
        except Exception as e:
            result.error_message = str(e)
            scan_logger.error(f"SNMP poll error for {ip_address}: {e}")
        
        return result
    
    async def poll_device_async(
        self,
        ip_address: str,
        community: str = None
    ) -> SNMPResult:
        """Async wrapper for poll_device."""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(
                executor, self.poll_device, ip_address, community
            )
    
    async def poll_devices(
        self,
        devices: List[Dict[str, str]],
        max_concurrent: int = 20
    ) -> List[SNMPResult]:
        """
        Poll multiple devices concurrently.
        
        Args:
            devices: List of dicts with 'ip_address' and optional 'snmp_community'
            max_concurrent: Maximum concurrent SNMP requests
        
        Returns:
            List of SNMPResult objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def poll_with_semaphore(device):
            async with semaphore:
                return await self.poll_device_async(
                    device['ip_address'],
                    device.get('snmp_community')
                )
        
        tasks = [poll_with_semaphore(d) for d in devices]
        results = await asyncio.gather(*tasks)
        
        return list(results)


# Singleton instance
snmp_poller = SNMPPoller()
