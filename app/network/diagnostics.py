"""
Network diagnostic utilities for DNS lookups and ICMP operations.

Provides DNS resolution, ping, and traceroute functionality with
Guardian integration and safe fallbacks for restricted environments.
"""

import asyncio
import socket
import subprocess
import platform
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from pydantic import BaseModel, Field

from app.network.guardian import Guardian, OperationType, get_guardian
from app.utils.logger import logger


class DNSRecord(BaseModel):
    """DNS resolution result."""
    
    hostname: str
    ip_addresses: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)
    resolution_time: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    error: Optional[str] = None


class PingResult(BaseModel):
    """ICMP ping result."""
    
    host: str
    ip_address: Optional[str] = None
    packets_sent: int = 0
    packets_received: int = 0
    packet_loss: float = 0.0
    min_rtt: Optional[float] = None
    max_rtt: Optional[float] = None
    avg_rtt: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool = False
    error: Optional[str] = None


class TracerouteHop(BaseModel):
    """Single hop in traceroute."""
    
    hop_number: int
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    rtt_ms: Optional[float] = None
    timeout: bool = False


class TracerouteResult(BaseModel):
    """Traceroute result."""
    
    destination: str
    hops: List[TracerouteHop] = Field(default_factory=list)
    max_hops_reached: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool = False
    error: Optional[str] = None


class NetworkDiagnostics:
    """
    Network diagnostic tools with Guardian integration.
    
    Features:
    - DNS lookups (A, AAAA, CNAME, MX records)
    - ICMP ping
    - Traceroute
    - Safe fallbacks for restricted environments
    - Guardian security validation
    """
    
    def __init__(self, guardian: Optional[Guardian] = None):
        """
        Initialize network diagnostics.
        
        Args:
            guardian: Guardian instance for security validation
        """
        self.guardian = guardian or get_guardian()
        self._platform = platform.system().lower()
        logger.info("NetworkDiagnostics initialized")
    
    async def _check_guardian(
        self,
        operation: OperationType,
        host: str
    ) -> bool:
        """
        Check Guardian approval for diagnostic operation.
        
        Args:
            operation: Type of operation
            host: Target host
            
        Returns:
            True if approved
            
        Raises:
            PermissionError: If blocked by Guardian
        """
        assessment = self.guardian.assess_risk(
            operation=operation,
            host=host,
            port=None
        )
        
        if not assessment.approved:
            error_msg = (
                f"Diagnostic operation blocked by Guardian: {operation.value} {host}\n"
                f"Risk Level: {assessment.level.value}\n"
                f"Reasons: {', '.join(assessment.reasons)}"
            )
            logger.warning(error_msg)
            raise PermissionError(error_msg)
        
        return True
    
    async def dns_lookup(
        self,
        hostname: str,
        record_type: str = "A"
    ) -> DNSRecord:
        """
        Perform DNS lookup.
        
        Args:
            hostname: Hostname to resolve
            record_type: DNS record type (A, AAAA, CNAME, MX)
            
        Returns:
            DNSRecord with resolution results
        """
        import time
        
        # Check Guardian
        await self._check_guardian(OperationType.DNS_LOOKUP, hostname)
        
        start_time = time.time()
        
        try:
            logger.info(f"DNS lookup: {hostname} ({record_type})")
            
            if record_type in ["A", "AAAA"]:
                # Standard address lookup
                loop = asyncio.get_event_loop()
                addr_info = await loop.getaddrinfo(
                    hostname,
                    None,
                    family=socket.AF_INET if record_type == "A" else socket.AF_INET6
                )
                
                ip_addresses = list(set([addr[4][0] for addr in addr_info]))
                aliases = []
                
            elif record_type == "CNAME":
                # CNAME lookup
                try:
                    import dns.resolver
                    answers = dns.resolver.resolve(hostname, 'CNAME')
                    aliases = [str(rdata.target) for rdata in answers]
                    ip_addresses = []
                except ImportError:
                    logger.warning("dnspython not installed, CNAME lookup not available")
                    return DNSRecord(
                        hostname=hostname,
                        error="CNAME lookup requires dnspython package"
                    )
                except Exception as e:
                    logger.error(f"CNAME lookup failed: {e}")
                    return DNSRecord(hostname=hostname, error=str(e))
            
            elif record_type == "MX":
                # MX record lookup
                try:
                    import dns.resolver
                    answers = dns.resolver.resolve(hostname, 'MX')
                    aliases = [str(rdata.exchange) for rdata in answers]
                    ip_addresses = []
                except ImportError:
                    logger.warning("dnspython not installed, MX lookup not available")
                    return DNSRecord(
                        hostname=hostname,
                        error="MX lookup requires dnspython package"
                    )
                except Exception as e:
                    logger.error(f"MX lookup failed: {e}")
                    return DNSRecord(hostname=hostname, error=str(e))
            
            else:
                return DNSRecord(
                    hostname=hostname,
                    error=f"Unsupported record type: {record_type}"
                )
            
            resolution_time = time.time() - start_time
            
            logger.info(
                f"DNS lookup successful: {hostname} -> {ip_addresses or aliases}"
            )
            
            return DNSRecord(
                hostname=hostname,
                ip_addresses=ip_addresses,
                aliases=aliases,
                resolution_time=resolution_time
            )
        
        except socket.gaierror as e:
            logger.error(f"DNS lookup failed: {hostname} - {e}")
            return DNSRecord(
                hostname=hostname,
                resolution_time=time.time() - start_time,
                error=f"DNS lookup failed: {e}"
            )
        except Exception as e:
            logger.error(f"DNS lookup error: {e}")
            return DNSRecord(
                hostname=hostname,
                resolution_time=time.time() - start_time,
                error=str(e)
            )
    
    async def ping(
        self,
        host: str,
        count: int = 4,
        timeout: int = 5
    ) -> PingResult:
        """
        Ping a host using ICMP.
        
        Args:
            host: Target host
            count: Number of ping packets
            timeout: Timeout in seconds
            
        Returns:
            PingResult with statistics
        """
        # Check Guardian
        await self._check_guardian(OperationType.ICMP_PING, host)
        
        logger.info(f"Pinging {host} with {count} packets")
        
        try:
            # Build ping command based on platform
            if self._platform == "windows":
                cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
            else:
                cmd = ["ping", "-c", str(count), "-W", str(timeout), host]
            
            # Execute ping
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode()
            
            # Parse output
            result = self._parse_ping_output(host, output)
            
            if result.packets_received > 0:
                logger.info(
                    f"Ping successful: {host} - "
                    f"{result.packets_received}/{result.packets_sent} packets, "
                    f"avg RTT: {result.avg_rtt:.2f}ms"
                )
            else:
                logger.warning(f"Ping failed: {host} - 100% packet loss")
            
            return result
        
        except FileNotFoundError:
            logger.error("Ping command not found")
            return PingResult(
                host=host,
                error="Ping command not available on this system"
            )
        except Exception as e:
            logger.error(f"Ping error: {e}")
            return PingResult(host=host, error=str(e))
    
    def _parse_ping_output(self, host: str, output: str) -> PingResult:
        """Parse ping command output."""
        import re
        
        result = PingResult(host=host)
        
        try:
            # Extract IP address
            ip_match = re.search(r'(?:from |Pinging )(\d+\.\d+\.\d+\.\d+)', output)
            if ip_match:
                result.ip_address = ip_match.group(1)
            
            # Extract packet statistics
            if self._platform == "windows":
                # Windows format: "Packets: Sent = 4, Received = 4, Lost = 0"
                sent_match = re.search(r'Sent = (\d+)', output)
                recv_match = re.search(r'Received = (\d+)', output)
                
                if sent_match:
                    result.packets_sent = int(sent_match.group(1))
                if recv_match:
                    result.packets_received = int(recv_match.group(1))
                
                # RTT: "Minimum = 0ms, Maximum = 0ms, Average = 0ms"
                min_match = re.search(r'Minimum = (\d+)ms', output)
                max_match = re.search(r'Maximum = (\d+)ms', output)
                avg_match = re.search(r'Average = (\d+)ms', output)
            else:
                # Unix format: "4 packets transmitted, 4 received, 0% packet loss"
                stats_match = re.search(
                    r'(\d+) packets transmitted, (\d+) received',
                    output
                )
                if stats_match:
                    result.packets_sent = int(stats_match.group(1))
                    result.packets_received = int(stats_match.group(2))
                
                # RTT: "rtt min/avg/max/mdev = 0.1/0.2/0.3/0.1 ms"
                rtt_match = re.search(
                    r'rtt min/avg/max/[^ ]+ = ([\d.]+)/([\d.]+)/([\d.]+)',
                    output
                )
                if rtt_match:
                    result.min_rtt = float(rtt_match.group(1))
                    result.avg_rtt = float(rtt_match.group(2))
                    result.max_rtt = float(rtt_match.group(3))
                else:
                    # Try alternative format
                    min_match = re.search(r'min=([\d.]+)', output)
                    max_match = re.search(r'max=([\d.]+)', output)
                    avg_match = re.search(r'avg=([\d.]+)', output)
            
            # Extract RTT values (if not already done)
            if result.min_rtt is None and min_match:
                result.min_rtt = float(min_match.group(1))
            if result.max_rtt is None and max_match:
                result.max_rtt = float(max_match.group(1))
            if result.avg_rtt is None and avg_match:
                result.avg_rtt = float(avg_match.group(1))
            
            # Calculate packet loss
            if result.packets_sent > 0:
                lost = result.packets_sent - result.packets_received
                result.packet_loss = (lost / result.packets_sent) * 100
            
            result.success = result.packets_received > 0
        
        except Exception as e:
            logger.error(f"Error parsing ping output: {e}")
            result.error = f"Failed to parse ping output: {e}"
        
        return result
    
    async def traceroute(
        self,
        host: str,
        max_hops: int = 30,
        timeout: int = 5
    ) -> TracerouteResult:
        """
        Perform traceroute to host.
        
        Args:
            host: Target host
            max_hops: Maximum number of hops
            timeout: Timeout per hop in seconds
            
        Returns:
            TracerouteResult with hop information
        """
        # Check Guardian
        await self._check_guardian(OperationType.ICMP_TRACEROUTE, host)
        
        logger.info(f"Traceroute to {host} (max {max_hops} hops)")
        
        try:
            # Build traceroute command
            if self._platform == "windows":
                cmd = ["tracert", "-h", str(max_hops), "-w", str(timeout * 1000), host]
            else:
                cmd = ["traceroute", "-m", str(max_hops), "-w", str(timeout), host]
            
            # Execute traceroute
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode()
            
            # Parse output
            result = self._parse_traceroute_output(host, output)
            
            logger.info(
                f"Traceroute completed: {host} - "
                f"{len(result.hops)} hops"
            )
            
            return result
        
        except FileNotFoundError:
            logger.error("Traceroute command not found")
            return TracerouteResult(
                destination=host,
                error="Traceroute command not available on this system"
            )
        except Exception as e:
            logger.error(f"Traceroute error: {e}")
            return TracerouteResult(destination=host, error=str(e))
    
    def _parse_traceroute_output(self, host: str, output: str) -> TracerouteResult:
        """Parse traceroute command output."""
        import re
        
        result = TracerouteResult(destination=host)
        
        try:
            lines = output.split('\n')
            
            for line in lines:
                # Skip header lines
                if not line.strip() or 'traceroute' in line.lower() or 'Tracing route' in line:
                    continue
                
                # Parse hop line
                if self._platform == "windows":
                    # Windows format: "  1    <1 ms    <1 ms    <1 ms  192.168.1.1"
                    match = re.match(r'\s*(\d+)\s+(?:(<?\d+)\s+ms\s+)?(?:(<?\d+)\s+ms\s+)?(?:(<?\d+)\s+ms\s+)?([\w\d\.\:\[\]]+)', line)
                else:
                    # Unix format: " 1  192.168.1.1 (192.168.1.1)  0.5 ms  0.3 ms  0.2 ms"
                    match = re.match(r'\s*(\d+)\s+(?:([\w\d\.\-]+)\s+)?\(([\d\.:]+)\)\s+([\d\.]+)\s+ms', line)
                
                if match:
                    if self._platform == "windows":
                        hop_num = int(match.group(1))
                        rtt = match.group(4) if match.group(4) else None
                        address = match.group(5)
                        
                        # Check for timeout
                        if '*' in line or 'Request timed out' in line:
                            hop = TracerouteHop(
                                hop_number=hop_num,
                                timeout=True
                            )
                        else:
                            hop = TracerouteHop(
                                hop_number=hop_num,
                                ip_address=address if re.match(r'^\d+\.\d+\.\d+\.\d+$', address) else None,
                                hostname=address if not re.match(r'^\d+\.\d+\.\d+\.\d+$', address) else None,
                                rtt_ms=float(rtt.lstrip('<')) if rtt and rtt != '*' else None
                            )
                    else:
                        hop_num = int(match.group(1))
                        hostname = match.group(2)
                        ip_address = match.group(3)
                        rtt = match.group(4)
                        
                        hop = TracerouteHop(
                            hop_number=hop_num,
                            ip_address=ip_address,
                            hostname=hostname,
                            rtt_ms=float(rtt)
                        )
                    
                    result.hops.append(hop)
            
            result.success = len(result.hops) > 0
            result.max_hops_reached = len(result.hops) >= 30
        
        except Exception as e:
            logger.error(f"Error parsing traceroute output: {e}")
            result.error = f"Failed to parse traceroute output: {e}"
        
        return result
    
    async def resolve_reverse(self, ip_address: str) -> Optional[str]:
        """
        Perform reverse DNS lookup.
        
        Args:
            ip_address: IP address to resolve
            
        Returns:
            Hostname or None if not found
        """
        try:
            await self._check_guardian(OperationType.DNS_LOOKUP, ip_address)
            
            loop = asyncio.get_event_loop()
            hostname, _, _ = await loop.run_in_executor(
                None,
                socket.gethostbyaddr,
                ip_address
            )
            
            logger.info(f"Reverse DNS: {ip_address} -> {hostname}")
            return hostname
        
        except Exception as e:
            logger.error(f"Reverse DNS lookup failed: {e}")
            return None
