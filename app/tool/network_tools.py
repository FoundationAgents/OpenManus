"""
Network tools for MCP integration.

Provides HTTP requests, WebSocket connections, DNS lookups, and ping
functionality through MCP interface with Guardian validation.
"""

import asyncio
from typing import Any, Dict, Optional

from app.network import (
    HTTPClientWithCaching,
    HTTPClientConfig,
    NetworkDiagnostics,
    WebSocketHandler,
    WebSocketConfig,
)
from app.tool.base import BaseTool, ToolResult
from app.config import config
from app.utils.logger import logger


class HTTPRequestTool(BaseTool):
    """Tool for making HTTP requests with caching."""
    
    name: str = "http_request"
    description: str = """Make HTTP requests with automatic caching and retry logic.
    Supports GET, POST, PUT, DELETE methods with Guardian security validation.
    Responses are cached based on configuration."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to request"
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
                "description": "HTTP method",
                "default": "GET"
            },
            "params": {
                "type": "object",
                "description": "Query parameters",
                "default": {}
            },
            "data": {
                "type": "object",
                "description": "Request body data",
                "default": None
            },
            "headers": {
                "type": "object",
                "description": "Additional headers",
                "default": {}
            },
            "use_cache": {
                "type": "boolean",
                "description": "Whether to use cache for GET requests",
                "default": True
            },
            "cache_ttl": {
                "type": "integer",
                "description": "Custom cache TTL in seconds",
                "default": None
            }
        },
        "required": ["url"]
    }
    
    def __init__(self):
        super().__init__()
        self._client: Optional[HTTPClientWithCaching] = None
    
    async def _get_client(self) -> HTTPClientWithCaching:
        """Get or create HTTP client."""
        if self._client is None:
            net_config = config.network
            
            client_config = HTTPClientConfig(
                enable_cache=net_config.enable_http_cache,
                cache_max_size=net_config.http_cache_max_size,
                cache_max_memory_mb=net_config.http_cache_max_memory_mb,
                cache_default_ttl=net_config.http_cache_default_ttl,
                cache_enable_persistence=net_config.http_cache_persist,
                timeout=net_config.http_timeout,
                max_retries=net_config.http_max_retries,
                verify_ssl=net_config.http_verify_ssl,
                enable_rate_limiting=net_config.enable_rate_limiting,
                rate_limit_per_second=net_config.rate_limit_per_second,
                rate_limit_burst=net_config.rate_limit_burst,
            )
            
            self._client = HTTPClientWithCaching(config=client_config)
        
        return self._client
    
    async def execute(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        **kwargs
    ) -> ToolResult:
        """Execute HTTP request."""
        try:
            logger.info(f"HTTP request: {method} {url}")
            
            client = await self._get_client()
            
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers,
                use_cache=use_cache,
                cache_ttl=cache_ttl
            )
            
            result = {
                "status_code": response.status_code,
                "headers": response.headers,
                "content": response.content,
                "url": response.url,
                "from_cache": response.from_cache,
                "request_time": response.request_time
            }
            
            return self.success_response(result)
        
        except PermissionError as e:
            return self.fail_response(f"Request blocked by Guardian: {e}")
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return self.fail_response(f"HTTP request failed: {e}")


class DNSLookupTool(BaseTool):
    """Tool for DNS lookups."""
    
    name: str = "dns_lookup"
    description: str = """Perform DNS lookups for hostnames.
    Supports A, AAAA, CNAME, and MX record types."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "hostname": {
                "type": "string",
                "description": "Hostname to resolve"
            },
            "record_type": {
                "type": "string",
                "enum": ["A", "AAAA", "CNAME", "MX"],
                "description": "DNS record type",
                "default": "A"
            }
        },
        "required": ["hostname"]
    }
    
    def __init__(self):
        super().__init__()
        self._diagnostics: Optional[NetworkDiagnostics] = None
    
    def _get_diagnostics(self) -> NetworkDiagnostics:
        """Get or create diagnostics instance."""
        if self._diagnostics is None:
            self._diagnostics = NetworkDiagnostics()
        return self._diagnostics
    
    async def execute(
        self,
        hostname: str,
        record_type: str = "A",
        **kwargs
    ) -> ToolResult:
        """Execute DNS lookup."""
        try:
            if not config.network.enable_diagnostics:
                return self.fail_response("Network diagnostics are disabled")
            
            logger.info(f"DNS lookup: {hostname} ({record_type})")
            
            diagnostics = self._get_diagnostics()
            result = await diagnostics.dns_lookup(hostname, record_type)
            
            if result.error:
                return self.fail_response(result.error)
            
            return self.success_response({
                "hostname": result.hostname,
                "ip_addresses": result.ip_addresses,
                "aliases": result.aliases,
                "resolution_time": result.resolution_time,
                "timestamp": result.timestamp.isoformat()
            })
        
        except PermissionError as e:
            return self.fail_response(f"DNS lookup blocked by Guardian: {e}")
        except Exception as e:
            logger.error(f"DNS lookup failed: {e}")
            return self.fail_response(f"DNS lookup failed: {e}")


class PingTool(BaseTool):
    """Tool for ICMP ping."""
    
    name: str = "ping"
    description: str = """Ping a host using ICMP.
    Returns packet statistics and round-trip times."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "host": {
                "type": "string",
                "description": "Host to ping"
            },
            "count": {
                "type": "integer",
                "description": "Number of ping packets",
                "default": 4
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 5
            }
        },
        "required": ["host"]
    }
    
    def __init__(self):
        super().__init__()
        self._diagnostics: Optional[NetworkDiagnostics] = None
    
    def _get_diagnostics(self) -> NetworkDiagnostics:
        """Get or create diagnostics instance."""
        if self._diagnostics is None:
            self._diagnostics = NetworkDiagnostics()
        return self._diagnostics
    
    async def execute(
        self,
        host: str,
        count: Optional[int] = None,
        timeout: int = 5,
        **kwargs
    ) -> ToolResult:
        """Execute ping."""
        try:
            if not config.network.enable_diagnostics:
                return self.fail_response("Network diagnostics are disabled")
            
            if count is None:
                count = config.network.ping_count
            
            logger.info(f"Pinging {host} with {count} packets")
            
            diagnostics = self._get_diagnostics()
            result = await diagnostics.ping(host, count, timeout)
            
            if result.error:
                return self.fail_response(result.error)
            
            return self.success_response({
                "host": result.host,
                "ip_address": result.ip_address,
                "packets_sent": result.packets_sent,
                "packets_received": result.packets_received,
                "packet_loss": result.packet_loss,
                "min_rtt": result.min_rtt,
                "max_rtt": result.max_rtt,
                "avg_rtt": result.avg_rtt,
                "success": result.success,
                "timestamp": result.timestamp.isoformat()
            })
        
        except PermissionError as e:
            return self.fail_response(f"Ping blocked by Guardian: {e}")
        except Exception as e:
            logger.error(f"Ping failed: {e}")
            return self.fail_response(f"Ping failed: {e}")


class TracerouteTool(BaseTool):
    """Tool for traceroute."""
    
    name: str = "traceroute"
    description: str = """Perform traceroute to a host.
    Returns the path and hop information to the destination."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "host": {
                "type": "string",
                "description": "Target host"
            },
            "max_hops": {
                "type": "integer",
                "description": "Maximum number of hops",
                "default": 30
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout per hop in seconds",
                "default": 5
            }
        },
        "required": ["host"]
    }
    
    def __init__(self):
        super().__init__()
        self._diagnostics: Optional[NetworkDiagnostics] = None
    
    def _get_diagnostics(self) -> NetworkDiagnostics:
        """Get or create diagnostics instance."""
        if self._diagnostics is None:
            self._diagnostics = NetworkDiagnostics()
        return self._diagnostics
    
    async def execute(
        self,
        host: str,
        max_hops: Optional[int] = None,
        timeout: int = 5,
        **kwargs
    ) -> ToolResult:
        """Execute traceroute."""
        try:
            if not config.network.enable_diagnostics:
                return self.fail_response("Network diagnostics are disabled")
            
            if max_hops is None:
                max_hops = config.network.traceroute_max_hops
            
            logger.info(f"Traceroute to {host} (max {max_hops} hops)")
            
            diagnostics = self._get_diagnostics()
            result = await diagnostics.traceroute(host, max_hops, timeout)
            
            if result.error:
                return self.fail_response(result.error)
            
            hops = [
                {
                    "hop_number": hop.hop_number,
                    "ip_address": hop.ip_address,
                    "hostname": hop.hostname,
                    "rtt_ms": hop.rtt_ms,
                    "timeout": hop.timeout
                }
                for hop in result.hops
            ]
            
            return self.success_response({
                "destination": result.destination,
                "hops": hops,
                "max_hops_reached": result.max_hops_reached,
                "success": result.success,
                "timestamp": result.timestamp.isoformat()
            })
        
        except PermissionError as e:
            return self.fail_response(f"Traceroute blocked by Guardian: {e}")
        except Exception as e:
            logger.error(f"Traceroute failed: {e}")
            return self.fail_response(f"Traceroute failed: {e}")


class GetCacheStatsTool(BaseTool):
    """Tool to get HTTP cache statistics."""
    
    name: str = "get_cache_stats"
    description: str = """Get statistics about the HTTP response cache.
    Returns hit rate, total entries, and memory usage."""
    
    parameters: dict = {
        "type": "object",
        "properties": {}
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Get cache statistics."""
        try:
            # Create a temporary client to get stats
            net_config = config.network
            
            client_config = HTTPClientConfig(
                enable_cache=net_config.enable_http_cache,
                cache_max_size=net_config.http_cache_max_size,
                cache_max_memory_mb=net_config.http_cache_max_memory_mb,
                cache_default_ttl=net_config.http_cache_default_ttl,
            )
            
            async with HTTPClientWithCaching(config=client_config) as client:
                stats = client.get_cache_stats()
                return self.success_response(stats)
        
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return self.fail_response(f"Failed to get cache stats: {e}")
