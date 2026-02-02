"""
Device Discovery Service - Enhanced Device Information Retrieval.
Provides MAC address lookup, vendor identification, OS detection, and port scanning.
Industry-grade device discovery from IP address.
"""

import asyncio
import socket
import subprocess
import platform
import re
import json
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from ..core import scan_logger


# OUI (Organizationally Unique Identifier) Database for vendor lookup
# Common network equipment vendors - expandable
OUI_DATABASE = {
    "00:00:0C": "Cisco",
    "00:01:42": "Cisco",
    "00:1A:A1": "Cisco",
    "00:50:56": "VMware",
    "00:0C:29": "VMware",
    "00:15:5D": "Microsoft Hyper-V",
    "08:00:27": "VirtualBox",
    "52:54:00": "QEMU/KVM",
    "00:1C:42": "Parallels",
    "00:16:3E": "Xen",
    "00:1A:11": "Google",
    "3C:D9:2B": "HP",
    "00:1E:68": "Quanta (Dell/HP)",
    "00:25:B5": "Dell",
    "00:14:4F": "Dell",
    "00:1E:C9": "Dell",
    "D4:BE:D9": "Dell",
    "00:17:A4": "HP",
    "00:21:5A": "HP",
    "00:25:64": "Dell",
    "F0:92:1C": "HP",
    "00:0D:56": "Dell",
    "00:06:5B": "Dell",
    "18:A9:05": "HP",
    "B4:99:BA": "HP",
    "EC:B1:D7": "HP",
    "00:1F:29": "HP",
    "F4:CE:46": "HP",
    "00:0B:82": "Grandstream",
    "00:1A:E9": "Nintendo",
    "00:17:31": "ASUS",
    "00:1E:8C": "ASUS",
    "54:04:A6": "ASUS",
    "00:1F:C6": "ASUS",
    "00:1C:B3": "Apple",
    "00:1E:C2": "Apple",
    "00:25:00": "Apple",
    "28:CF:DA": "Apple",
    "3C:15:C2": "Apple",
    "60:03:08": "Apple",
    "A4:5E:60": "Apple",
    "70:56:81": "Apple",
    "00:0A:95": "Apple",
    "00:0D:93": "Apple",
    "00:26:08": "DLink",
    "00:1B:11": "DLink",
    "00:22:B0": "DLink",
    "28:10:7B": "DLink",
    "00:1F:33": "Netgear",
    "00:24:B2": "Netgear",
    "00:26:F2": "Netgear",
    "20:4E:7F": "Netgear",
    "C0:FF:D4": "Netgear",
    "00:14:BF": "Linksys",
    "00:1A:70": "Linksys",
    "00:21:29": "Linksys",
    "00:23:69": "Linksys",
    "C0:C1:C0": "Linksys",
    "00:1E:58": "D-Link",
    "00:50:BA": "D-Link",
    "1C:7E:E5": "D-Link",
    "28:EE:52": "TP-Link",
    "54:C8:0F": "TP-Link",
    "60:E3:27": "TP-Link",
    "A0:F3:C1": "TP-Link",
    "C0:4A:00": "TP-Link",
    "E8:DE:27": "TP-Link",
    "50:C7:BF": "TP-Link",
    "00:18:E7": "Aruba",
    "00:0B:86": "Aruba",
    "00:1A:1E": "Aruba",
    "24:DE:C6": "Aruba",
    "40:E3:D6": "Aruba",
    "6C:C2:17": "Aruba",
    "00:09:0F": "Fortinet",
    "00:60:6E": "Davicom (Realtek)",
    "00:E0:4C": "Realtek",
    "52:54:AB": "Realtek",
    "00:1B:21": "Intel",
    "00:1E:67": "Intel",
    "00:1F:3B": "Intel",
    "00:22:FA": "Intel",
    "3C:97:0E": "Intel",
    "68:05:CA": "Intel",
    "84:3A:4B": "Intel",
    "AC:22:0B": "Intel",
    "B4:96:91": "Intel",
    "F4:6D:04": "Intel",
    "00:1D:09": "Dell",
    "14:FE:B5": "Dell",
    "18:A9:58": "Dell",
    "18:66:DA": "Dell",
    "24:B6:FD": "Dell",
    "34:17:EB": "Dell",
    "44:A8:42": "Dell",
    "5C:26:0A": "Dell",
    "74:86:7A": "Dell",
    "B0:83:FE": "Dell",
    "F8:BC:12": "Dell",
    # Mobile Devices
    "00:BB:3A": "Motorola",
    "00:0C:E5": "Motorola",
    "00:14:9A": "Motorola",
    "00:12:C9": "Motorola",
    "A4:70:D6": "Motorola",
    "D8:B1:2A": "Motorola",
    "E8:6D:CB": "Motorola",
    "00:1E:B2": "Samsung",
    "00:21:19": "Samsung",
    "00:26:37": "Samsung",
    "50:01:BB": "Samsung",
    "50:CC:F8": "Samsung",
    "5C:0A:5B": "Samsung",
    "5C:F6:DC": "Samsung",
    "60:AF:6D": "Samsung",
    "78:52:1A": "Samsung",
    "94:35:0A": "Samsung",
    "B4:3A:28": "Samsung",
    "C4:42:02": "Samsung",
    "D0:22:BE": "Samsung",
    "D0:66:7B": "Samsung",
    "E4:7C:F9": "Samsung",
    "F4:09:D8": "Samsung",
    "F8:04:2E": "Samsung",
    "00:27:09": "Nintendo",
    "00:22:D7": "Nintendo",
    "00:24:1E": "OnePlus",
    "00:17:FA": "Microsoft",
    "00:1D:D8": "Microsoft",
    "7C:1E:52": "Microsoft",
    "28:18:78": "Microsoft",
    "60:45:BD": "Microsoft",
    "00:24:D6": "Google",
    "3C:5A:B4": "Google",
    "54:60:09": "Google",
    "94:EB:2C": "Google",
    "F4:F5:E8": "Google",
    "00:1A:2B": "Xiaomi",
    "28:6C:07": "Xiaomi",
    "34:CE:00": "Xiaomi",
    "58:44:98": "Xiaomi",
    "64:09:80": "Xiaomi",
    "78:02:F8": "Xiaomi",
    "7C:1D:D9": "Xiaomi",
    "8C:BE:BE": "Xiaomi",
    "9C:99:A0": "Xiaomi",
    "B0:E2:35": "Xiaomi",
    "C4:6A:B7": "Xiaomi",
    "E4:AA:EC": "Xiaomi",
    "F8:A4:5F": "Xiaomi",
    "18:59:36": "Xiaomi",
    "50:8F:4C": "Xiaomi",
    "A4:77:33": "Google Pixel",
    "14:C9:13": "Huawei",
    "24:09:95": "Huawei",
    "34:CD:BE": "Huawei",
    "48:46:FB": "Huawei",
    "54:25:EA": "Huawei",
    "60:DE:44": "Huawei",
    "70:72:3C": "Huawei",
    "7C:60:97": "Huawei",
    "88:B1:11": "Huawei",
    "94:04:9C": "Huawei",
    "A4:BE:2B": "Huawei",
    "B4:CD:27": "Huawei",
    "D4:40:F0": "Huawei",
    "E0:19:1D": "Huawei",
    "F8:3D:FF": "Huawei",
    "00:21:6B": "OPPO",
    "A4:3B:FA": "OPPO",
    "58:1D:D8": "Realme",
    "00:1C:26": "Vivo",
    "54:CD:EE": "Vivo",
}


# Common ports to scan
COMMON_PORTS = {
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    135: "RPC",
    139: "NetBIOS",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    993: "IMAPS",
    995: "POP3S",
    1433: "MSSQL",
    1521: "Oracle",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    5900: "VNC",
    6379: "Redis",
    8080: "HTTP-Alt",
    8443: "HTTPS-Alt",
    27017: "MongoDB",
}


@dataclass
class DeviceDetails:
    """Complete device details discovered from IP."""
    ip_address: str
    mac_address: Optional[str] = None
    vendor: Optional[str] = None
    os_type: Optional[str] = None
    os_confidence: int = 0  # 0-100%
    hostname: Optional[str] = None
    netbios_name: Optional[str] = None
    open_ports: List[Dict[str, any]] = field(default_factory=list)
    ttl: Optional[int] = None
    discovery_time_seconds: float = 0.0


class DeviceDiscoveryService:
    """
    Enhanced device discovery service.
    Retrieves detailed information about network devices from IP address.
    """
    
    def __init__(self, port_scan_timeout: float = 0.5, max_workers: int = 20):
        self.port_scan_timeout = port_scan_timeout
        self.max_workers = max_workers
        self.is_windows = platform.system().lower() == "windows"
    
    def get_mac_from_arp(self, ip_address: str) -> Optional[str]:
        """
        Get MAC address from ARP cache.
        Works on both Windows and Linux.
        """
        try:
            if self.is_windows:
                # Windows: arp -a <ip>
                result = subprocess.run(
                    ["arp", "-a", ip_address],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                output = result.stdout
                
                # Parse: "192.168.1.1    00-1a-2b-3c-4d-5e    dynamic"
                mac_match = re.search(
                    r"([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}",
                    output
                )
                if mac_match:
                    # Normalize to colon-separated uppercase
                    mac = mac_match.group().replace("-", ":").upper()
                    return mac
            else:
                # Linux: arp -n <ip> or ip neigh show <ip>
                result = subprocess.run(
                    ["arp", "-n", ip_address],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                output = result.stdout
                
                mac_match = re.search(
                    r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}",
                    output
                )
                if mac_match:
                    return mac_match.group().upper()
            
            return None
            
        except Exception as e:
            scan_logger.debug(f"ARP lookup failed for {ip_address}: {e}")
            return None
    
    def get_vendor_from_mac(self, mac_address: str) -> Optional[str]:
        """
        Identify vendor from MAC address using OUI database.
        """
        if not mac_address:
            return None
        
        # Get first 3 octets (OUI)
        oui = mac_address[:8].upper()
        
        # Direct lookup
        if oui in OUI_DATABASE:
            return OUI_DATABASE[oui]
        
        # Try with different separator
        oui_dash = oui.replace(":", "-")
        if oui_dash in OUI_DATABASE:
            return OUI_DATABASE[oui_dash]
        
        return "Unknown"
    
    def detect_os_from_ttl(self, ip_address: str) -> Tuple[Optional[str], int, Optional[int]]:
        """
        Detect operating system based on TTL value from ping response.
        Common TTL defaults:
        - Windows: 128
        - Linux/Unix: 64
        - Network devices (Cisco, etc.): 255
        - Solaris/AIX: 254
        
        Returns: (os_type, confidence_percent, raw_ttl)
        """
        try:
            if self.is_windows:
                cmd = ["ping", "-n", "1", "-w", "1000", ip_address]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                cmd = ["ping", "-c", "1", "-W", "1", ip_address]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            
            output = result.stdout
            
            # Extract TTL
            ttl_match = re.search(r"ttl[=:](\d+)", output, re.IGNORECASE)
            if not ttl_match:
                return None, 0, None
            
            ttl = int(ttl_match.group(1))
            
            # Determine OS based on TTL
            if ttl <= 64:
                # Likely Linux/Unix (started at 64, decremented by hops)
                return "Linux/Unix", 80, ttl
            elif ttl <= 128:
                # Likely Windows (started at 128, decremented by hops)
                return "Windows", 85, ttl
            elif ttl <= 255:
                # Likely network device or Solaris
                if ttl >= 250:
                    return "Network Device", 75, ttl
                else:
                    return "Unix/Solaris", 60, ttl
            
            return "Unknown", 20, ttl
            
        except Exception as e:
            scan_logger.debug(f"OS detection failed for {ip_address}: {e}")
            return None, 0, None
    
    def detect_os_from_hostname(self, hostname: str, vendor: str = None) -> Tuple[Optional[str], int]:
        """
        Detect operating system based on hostname patterns.
        More accurate than TTL for mobile devices.
        
        Returns: (os_type, confidence_percent)
        """
        if not hostname:
            return None, 0
        
        hostname_lower = hostname.lower()
        
        # Android device patterns
        android_patterns = [
            "android", "galaxy", "pixel", "oneplus", "redmi", "poco", "realme",
            "oppo", "vivo", "huawei", "honor", "xiaomi", "mi-", "moto", "motorola",
            "samsung", "note", "tab", "pad", "droid", "nexus", "-phone", 
            "sm-", "gt-", "xt", "lenovo"
        ]
        
        # iOS device patterns
        ios_patterns = [
            "iphone", "ipad", "ipod", "apple", "macbook", "imac", "macpro",
            "mac-", "airpods", "watch", "homepod"
        ]
        
        # Windows patterns
        windows_patterns = [
            "desktop-", "laptop-", "pc-", "win", "msft", "surface",
            "workstation", "-pc", "thinkpad", "elitebook", "latitude"
        ]
        
        # Linux patterns
        linux_patterns = [
            "ubuntu", "debian", "centos", "fedora", "arch", "mint",
            "raspberrypi", "raspberry", "pi-", "linux", "srv-", "server"
        ]
        
        # Router/Network device patterns
        network_patterns = [
            "router", "gateway", "gw", "switch", "ap-", "access", "mesh",
            "firewall", "fw-", "proxy", "nas", "bbrouter", "rtkgw"
        ]
        
        # Check Android first (most common mobile)
        for pattern in android_patterns:
            if pattern in hostname_lower:
                return "Android", 90
        
        # Check vendor for mobile devices
        if vendor:
            vendor_lower = vendor.lower()
            android_vendors = ["samsung", "motorola", "xiaomi", "huawei", "oppo", 
                             "vivo", "realme", "oneplus", "google pixel"]
            for av in android_vendors:
                if av in vendor_lower:
                    return "Android", 85
        
        # Check iOS
        for pattern in ios_patterns:
            if pattern in hostname_lower:
                return "iOS/macOS", 90
        
        if vendor and "apple" in vendor.lower():
            return "iOS/macOS", 85
        
        # Check Windows
        for pattern in windows_patterns:
            if pattern in hostname_lower:
                return "Windows", 85
        
        # Check network devices
        for pattern in network_patterns:
            if pattern in hostname_lower:
                return "Network Device", 80
        
        # Check Linux
        for pattern in linux_patterns:
            if pattern in hostname_lower:
                return "Linux", 85
        
        return None, 0
    
    def scan_port(self, ip_address: str, port: int) -> bool:
        """
        Check if a single port is open using TCP connect.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.port_scan_timeout)
            result = sock.connect_ex((ip_address, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def scan_common_ports(self, ip_address: str) -> List[Dict[str, any]]:
        """
        Scan common ports on the device.
        Returns list of open ports with service names.
        """
        open_ports = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Create futures for all ports
            future_to_port = {
                executor.submit(self.scan_port, ip_address, port): (port, name)
                for port, name in COMMON_PORTS.items()
            }
            
            for future in future_to_port:
                port, name = future_to_port[future]
                try:
                    if future.result():
                        open_ports.append({
                            "port": port,
                            "service": name,
                            "state": "open"
                        })
                except:
                    pass
        
        # Sort by port number
        open_ports.sort(key=lambda x: x["port"])
        
        return open_ports
    
    def grab_banner(self, ip_address: str, port: int, timeout: float = 2.0) -> Optional[str]:
        """
        Attempt to grab service banner from an open port.
        Returns the banner string or None if unavailable.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip_address, port))
            
            # Send a probe request for HTTP/HTTPS
            if port in [80, 8080, 8000]:
                sock.send(b"HEAD / HTTP/1.0\r\n\r\n")
            elif port in [443, 8443]:
                # Skip SSL ports for now (would need SSL wrapper)
                sock.close()
                return "HTTPS (SSL/TLS)"
            elif port == 22:
                # SSH sends banner immediately
                pass
            elif port == 21:
                # FTP sends banner immediately  
                pass
            elif port == 25:
                # SMTP sends banner immediately
                pass
            else:
                # Generic probe
                sock.send(b"\r\n")
            
            # Try to receive banner
            banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
            sock.close()
            
            # Clean and truncate banner
            if banner:
                # Remove control characters and limit length
                banner = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', banner)[:100]
                return banner if banner else None
            
            return None
            
        except Exception as e:
            return None
    
    def scan_ports_with_banners(self, ip_address: str) -> List[Dict[str, any]]:
        """
        Scan common ports and grab banners for open ones.
        More thorough than basic port scan.
        """
        # First do quick port scan
        open_ports = self.scan_common_ports(ip_address)
        
        # Then grab banners for open ports (limited to first 5 for speed)
        for port_info in open_ports[:5]:
            banner = self.grab_banner(ip_address, port_info["port"])
            if banner:
                port_info["banner"] = banner
                
                # Try to extract version info from banner
                version = self._extract_version_from_banner(banner)
                if version:
                    port_info["version"] = version
        
        return open_ports
    
    def _extract_version_from_banner(self, banner: str) -> Optional[str]:
        """Extract version string from service banner."""
        if not banner:
            return None
        
        # Common patterns
        patterns = [
            r'(OpenSSH[_\s][0-9.]+)',  # SSH
            r'(Apache/[0-9.]+)',       # Apache
            r'(nginx/[0-9.]+)',        # nginx
            r'(Microsoft-IIS/[0-9.]+)', # IIS
            r'(MySQL\s*[0-9.]+)',      # MySQL
            r'(PostgreSQL\s*[0-9.]+)', # PostgreSQL
            r'(vsftpd\s*[0-9.]+)',     # vsftpd
            r'(ProFTPD\s*[0-9.]+)',    # ProFTPD
            r'(Postfix)',              # Postfix
            r'(Exim\s*[0-9.]+)',       # Exim
        ]
        
        for pattern in patterns:
            match = re.search(pattern, banner, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def get_netbios_name(self, ip_address: str) -> Optional[str]:
        """
        Get NetBIOS name for Windows hosts.
        Uses nbtstat on Windows.
        """
        if not self.is_windows:
            return None
        
        try:
            result = subprocess.run(
                ["nbtstat", "-A", ip_address],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            output = result.stdout
            
            # Parse NetBIOS name (first entry with <00>)
            for line in output.split("\n"):
                if "<00>" in line and "UNIQUE" in line:
                    parts = line.split()
                    if parts:
                        return parts[0].strip()
            
            return None
            
        except Exception as e:
            scan_logger.debug(f"NetBIOS lookup failed for {ip_address}: {e}")
            return None
    
    async def discover_device(self, ip_address: str, full_scan: bool = True) -> DeviceDetails:
        """
        Perform complete device discovery.
        
        Args:
            ip_address: Target IP address
            full_scan: If True, includes port scanning (slower)
        
        Returns:
            DeviceDetails with all discovered information
        """
        import time
        start_time = time.time()
        
        details = DeviceDetails(ip_address=ip_address)
        
        loop = asyncio.get_event_loop()
        
        # Run discovery tasks
        with ThreadPoolExecutor(max_workers=5) as executor:
            # MAC address lookup
            mac_future = loop.run_in_executor(
                executor, self.get_mac_from_arp, ip_address
            )
            
            # OS detection (TTL-based)
            os_future = loop.run_in_executor(
                executor, self.detect_os_from_ttl, ip_address
            )
            
            # DNS hostname
            hostname_future = loop.run_in_executor(
                executor, self._resolve_hostname, ip_address
            )
            
            # NetBIOS name (Windows only)
            if self.is_windows:
                netbios_future = loop.run_in_executor(
                    executor, self.get_netbios_name, ip_address
                )
            
            # Wait for basic discovery
            details.mac_address = await mac_future
            details.vendor = self.get_vendor_from_mac(details.mac_address)
            
            os_type_ttl, confidence_ttl, ttl = await os_future
            details.ttl = ttl
            
            details.hostname = await hostname_future
            
            if self.is_windows:
                details.netbios_name = await netbios_future
            
            # Use hostname-based OS detection first (more accurate for mobile devices)
            os_type_hostname, confidence_hostname = self.detect_os_from_hostname(
                details.hostname or details.netbios_name, 
                details.vendor
            )
            
            # Use hostname-based detection if confident, otherwise fall back to TTL
            if os_type_hostname and confidence_hostname > 70:
                details.os_type = os_type_hostname
                details.os_confidence = confidence_hostname
            elif os_type_ttl:
                details.os_type = os_type_ttl
                details.os_confidence = confidence_ttl
            else:
                details.os_type = None
                details.os_confidence = 0
        
        # Port scanning (can be slow)
        if full_scan:
            details.open_ports = await loop.run_in_executor(
                None, self.scan_common_ports, ip_address
            )
        
        details.discovery_time_seconds = time.time() - start_time
        
        scan_logger.info(
            f"Discovered {ip_address}: MAC={details.mac_address}, "
            f"Vendor={details.vendor}, OS={details.os_type}, "
            f"Ports={len(details.open_ports)}"
        )
        
        return details
    
    def _resolve_hostname(self, ip_address: str) -> Optional[str]:
        """Resolve hostname via DNS."""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip_address)
            return hostname
        except:
            return None


# Singleton instance
device_discovery = DeviceDiscoveryService()
