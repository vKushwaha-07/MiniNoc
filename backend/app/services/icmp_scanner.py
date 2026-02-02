"""
ICMP Scanner Service for Network Device Discovery and Health Monitoring.
Provides subnet scanning and individual host ping functionality.
FIXED: Improved Windows ping parsing for accurate reachability detection.
"""

import asyncio
import ipaddress
import subprocess
import platform
import time
import re
from dataclasses import dataclass
from typing import Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor

from ..core import scan_logger, settings


@dataclass
class PingResult:
    """Result of an ICMP ping operation."""
    ip_address: str
    is_reachable: bool
    latency_ms: Optional[float] = None
    packets_sent: int = 0
    packets_received: int = 0
    packet_loss_percent: float = 100.0
    error_message: Optional[str] = None


class ICMPScanner:
    """
    ICMP-based network scanner for device discovery and health checks.
    Uses system ping command for cross-platform compatibility.
    """
    
    def __init__(
        self,
        ping_count: int = None,
        timeout_seconds: float = None,
        max_concurrent: int = 50
    ):
        self.ping_count = ping_count or settings.PING_COUNT
        self.timeout_seconds = timeout_seconds or settings.PING_TIMEOUT_SECONDS
        self.max_concurrent = max_concurrent
        self.is_windows = platform.system().lower() == "windows"
        
    def _build_ping_command(self, ip_address: str) -> List[str]:
        """Build platform-specific ping command."""
        if self.is_windows:
            return [
                "ping",
                "-n", str(self.ping_count),
                "-w", str(int(self.timeout_seconds * 1000)),  # Windows uses ms
                ip_address
            ]
        else:
            return [
                "ping",
                "-c", str(self.ping_count),
                "-W", str(int(self.timeout_seconds)),
                ip_address
            ]
    
    def _parse_windows_ping(self, ip_address: str, output: str, returncode: int) -> PingResult:
        """
        Parse Windows ping output with robust pattern matching.
        Handles various failure cases properly.
        """
        result = PingResult(
            ip_address=ip_address,
            is_reachable=False,
            packets_sent=self.ping_count,
            packets_received=0,
            packet_loss_percent=100.0
        )
        
        # Check for common failure patterns FIRST
        failure_patterns = [
            "Destination host unreachable",
            "Request timed out",
            "Ping request could not find host",
            "Transmit failed",
            "General failure",
            "PING: transmit failed",
            "TTL expired in transit",
            "could not find host"
        ]
        
        output_lower = output.lower()
        for pattern in failure_patterns:
            if pattern.lower() in output_lower:
                result.is_reachable = False
                result.error_message = pattern
                scan_logger.debug(f"{ip_address}: {pattern}")
                
                # Still try to parse received count
                try:
                    if "received = " in output_lower:
                        match = re.search(r"received\s*=\s*(\d+)", output, re.IGNORECASE)
                        if match:
                            result.packets_received = int(match.group(1))
                except:
                    pass
                
                return result
        
        try:
            # Parse packets: "Sent = 4, Received = 4, Lost = 0"
            sent_match = re.search(r"Sent\s*=\s*(\d+)", output, re.IGNORECASE)
            recv_match = re.search(r"Received\s*=\s*(\d+)", output, re.IGNORECASE)
            
            if sent_match:
                result.packets_sent = int(sent_match.group(1))
            if recv_match:
                result.packets_received = int(recv_match.group(1))
            
            # Parse latency: "Average = 10ms" or "Average = <1ms"
            avg_match = re.search(r"Average\s*=\s*<?(\d+)ms", output, re.IGNORECASE)
            if avg_match:
                result.latency_ms = float(avg_match.group(1))
            else:
                # Try parsing from "time=10ms" or "time<1ms"
                time_matches = re.findall(r"time[=<](\d+)ms", output, re.IGNORECASE)
                if time_matches:
                    latencies = [float(t) for t in time_matches]
                    result.latency_ms = sum(latencies) / len(latencies)
            
            # Calculate packet loss
            if result.packets_sent > 0:
                result.packet_loss_percent = (
                    (result.packets_sent - result.packets_received) / result.packets_sent * 100
                )
            
            # Only mark as reachable if we actually received packets
            result.is_reachable = result.packets_received > 0
            
        except Exception as e:
            scan_logger.warning(f"Error parsing ping output for {ip_address}: {e}")
            result.error_message = str(e)
        
        return result
    
    def _parse_linux_ping(self, ip_address: str, output: str, returncode: int) -> PingResult:
        """Parse Linux/Mac ping output."""
        result = PingResult(
            ip_address=ip_address,
            is_reachable=False,
            packets_sent=self.ping_count,
            packets_received=0,
            packet_loss_percent=100.0
        )
        
        try:
            # Parse: "4 packets transmitted, 2 received, 50% packet loss"
            stats_match = re.search(
                r"(\d+)\s+packets?\s+transmitted,\s*(\d+)\s+received",
                output, re.IGNORECASE
            )
            if stats_match:
                result.packets_sent = int(stats_match.group(1))
                result.packets_received = int(stats_match.group(2))
            
            # Parse latency: "rtt min/avg/max/mdev = 0.1/0.2/0.3/0.0 ms"
            rtt_match = re.search(
                r"rtt\s+min/avg/max/mdev\s*=\s*[\d.]+/([\d.]+)/",
                output, re.IGNORECASE
            )
            if rtt_match:
                result.latency_ms = float(rtt_match.group(1))
            
            # Calculate packet loss
            if result.packets_sent > 0:
                result.packet_loss_percent = (
                    (result.packets_sent - result.packets_received) / result.packets_sent * 100
                )
            
            result.is_reachable = result.packets_received > 0
            
        except Exception as e:
            scan_logger.warning(f"Error parsing ping output for {ip_address}: {e}")
            result.error_message = str(e)
        
        return result
    
    def ping_host(self, ip_address: str) -> PingResult:
        """
        Ping a single host and return the result.
        Synchronous version for use in thread pools.
        """
        command = self._build_ping_command(ip_address)
        
        try:
            # Run ping command with proper timeout
            max_wait = self.timeout_seconds * self.ping_count + 5
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=max_wait,
                creationflags=subprocess.CREATE_NO_WINDOW if self.is_windows else 0
            )
            
            output = process.stdout + process.stderr
            
            # Parse based on platform
            if self.is_windows:
                return self._parse_windows_ping(ip_address, output, process.returncode)
            else:
                return self._parse_linux_ping(ip_address, output, process.returncode)
            
        except subprocess.TimeoutExpired:
            scan_logger.warning(f"Ping timeout for {ip_address}")
            return PingResult(
                ip_address=ip_address,
                is_reachable=False,
                packets_sent=self.ping_count,
                error_message="Ping timeout"
            )
        except FileNotFoundError:
            scan_logger.error(f"Ping command not found")
            return PingResult(
                ip_address=ip_address,
                is_reachable=False,
                packets_sent=self.ping_count,
                error_message="Ping command not found"
            )
        except Exception as e:
            scan_logger.error(f"Ping error for {ip_address}: {e}")
            return PingResult(
                ip_address=ip_address,
                is_reachable=False,
                packets_sent=self.ping_count,
                error_message=str(e)
            )
    
    async def ping_host_async(self, ip_address: str) -> PingResult:
        """Async wrapper for ping_host using thread pool."""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            return await loop.run_in_executor(executor, self.ping_host, ip_address)
    
    async def scan_subnet(
        self,
        subnet: str,
        progress_callback=None
    ) -> Tuple[List[PingResult], float]:
        """
        Scan an entire subnet for active hosts.
        
        Args:
            subnet: CIDR notation subnet (e.g., "192.168.1.0/24")
            progress_callback: Optional callback(current, total) for progress updates
        
        Returns:
            Tuple of (list of PingResults, duration in seconds)
        """
        start_time = time.time()
        
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            hosts = list(network.hosts())
        except ValueError as e:
            scan_logger.error(f"Invalid subnet: {subnet} - {e}")
            return [], 0
        
        total_hosts = len(hosts)
        scan_logger.info(f"Starting scan of {subnet} ({total_hosts} hosts)")
        
        results = []
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def scan_with_semaphore(ip):
            async with semaphore:
                return await self.ping_host_async(str(ip))
        
        # Create tasks for all hosts
        tasks = [scan_with_semaphore(ip) for ip in hosts]
        
        # Execute with progress tracking
        completed = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            completed += 1
            
            if progress_callback:
                progress_callback(completed, total_hosts)
        
        duration = time.time() - start_time
        reachable = sum(1 for r in results if r.is_reachable)
        
        scan_logger.info(
            f"Scan complete: {reachable}/{total_hosts} hosts reachable in {duration:.2f}s"
        )
        
        return results, duration
    
    async def health_check_hosts(self, ip_addresses: List[str]) -> List[PingResult]:
        """
        Perform health check on a list of known hosts.
        Optimized for monitoring existing devices.
        """
        if not ip_addresses:
            return []
        
        scan_logger.info(f"Health check on {len(ip_addresses)} devices")
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def check_with_semaphore(ip):
            async with semaphore:
                return await self.ping_host_async(ip)
        
        tasks = [check_with_semaphore(ip) for ip in ip_addresses]
        results = await asyncio.gather(*tasks)
        
        # Log summary
        reachable = sum(1 for r in results if r.is_reachable)
        scan_logger.info(f"Health check complete: {reachable}/{len(ip_addresses)} UP")
        
        return list(results)


# Singleton instance for global use
icmp_scanner = ICMPScanner()
