"""
API integration manager for defining and managing external API profiles.

Provides centralized management of API configurations, authentication,
rate limits, and Guardian-enforced access control.
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from app.network.client import HTTPClientWithCaching, HTTPClientConfig
from app.network.guardian import Guardian, NetworkPolicy, OperationType, get_guardian
from app.utils.logger import logger


class AuthType(str, Enum):
    """Authentication types for API integration."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer"
    BASIC = "basic"
    OAUTH2 = "oauth2"
    CUSTOM = "custom"


class HTTPMethod(str, Enum):
    """Allowed HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class APIAuthConfig(BaseModel):
    """Authentication configuration for API."""
    
    auth_type: AuthType
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"
    bearer_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    custom_headers: Dict[str, str] = Field(default_factory=dict)


class APIEndpoint(BaseModel):
    """Definition of an API endpoint."""
    
    path: str
    methods: Set[HTTPMethod] = Field(default_factory=lambda: {HTTPMethod.GET})
    description: str = ""
    rate_limit_per_minute: Optional[int] = None
    requires_auth: bool = True
    cache_ttl: Optional[int] = None


class APIProfile(BaseModel):
    """Complete API integration profile."""
    
    profile_id: str
    name: str
    description: str
    base_url: str
    auth_config: Optional[APIAuthConfig] = None
    endpoints: Dict[str, APIEndpoint] = Field(default_factory=dict)
    allowed_operations: Set[OperationType] = Field(default_factory=set)
    rate_limit_per_minute: int = 60
    timeout: float = 30.0
    verify_ssl: bool = True
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        arbitrary_types_allowed = True


class APICallLog(BaseModel):
    """Log entry for API call."""
    
    profile_id: str
    endpoint: str
    method: str
    status_code: Optional[int] = None
    success: bool = False
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    request_time: float = 0.0


class APIIntegrationManager:
    """
    Manager for API integrations with Guardian-enforced access control.
    
    Features:
    - API profile management
    - Authentication handling
    - Rate limiting per API
    - Guardian policy enforcement
    - Persistent storage
    - Call logging
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        guardian: Optional[Guardian] = None
    ):
        """
        Initialize API integration manager.
        
        Args:
            storage_path: Path to store API profiles
            guardian: Guardian instance for security
        """
        self.storage_path = Path(storage_path) if storage_path else Path("config/api_profiles")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.guardian = guardian or get_guardian()
        
        self.profiles: Dict[str, APIProfile] = {}
        self.clients: Dict[str, HTTPClientWithCaching] = {}
        self.call_logs: List[APICallLog] = []
        
        # Load existing profiles
        self._load_profiles()
        
        logger.info(
            f"APIIntegrationManager initialized with {len(self.profiles)} profiles"
        )
    
    def _load_profiles(self):
        """Load API profiles from storage."""
        if not self.storage_path.exists():
            return
        
        for profile_file in self.storage_path.glob("*.json"):
            try:
                with profile_file.open('r') as f:
                    data = json.load(f)
                    profile = APIProfile(**data)
                    self.profiles[profile.profile_id] = profile
                    logger.debug(f"Loaded API profile: {profile.name}")
            except Exception as e:
                logger.error(f"Failed to load profile {profile_file}: {e}")
    
    def _save_profile(self, profile: APIProfile):
        """Save API profile to storage."""
        try:
            profile_file = self.storage_path / f"{profile.profile_id}.json"
            with profile_file.open('w') as f:
                # Convert to dict and handle non-serializable types
                data = profile.dict()
                data['created_at'] = profile.created_at.isoformat()
                data['updated_at'] = profile.updated_at.isoformat()
                data['allowed_operations'] = list(profile.allowed_operations)
                
                # Convert endpoints
                for endpoint_key, endpoint in data['endpoints'].items():
                    endpoint['methods'] = list(endpoint['methods'])
                
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved API profile: {profile.name}")
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")
    
    def create_profile(
        self,
        profile_id: str,
        name: str,
        base_url: str,
        description: str = "",
        auth_config: Optional[APIAuthConfig] = None,
        **kwargs
    ) -> APIProfile:
        """
        Create new API profile.
        
        Args:
            profile_id: Unique profile identifier
            name: Profile name
            base_url: Base URL for API
            description: Profile description
            auth_config: Authentication configuration
            **kwargs: Additional profile settings
            
        Returns:
            Created APIProfile
            
        Raises:
            ValueError: If profile_id already exists
        """
        if profile_id in self.profiles:
            raise ValueError(f"Profile {profile_id} already exists")
        
        profile = APIProfile(
            profile_id=profile_id,
            name=name,
            description=description,
            base_url=base_url,
            auth_config=auth_config,
            **kwargs
        )
        
        self.profiles[profile_id] = profile
        self._save_profile(profile)
        
        logger.info(f"Created API profile: {name} ({profile_id})")
        
        return profile
    
    def update_profile(self, profile_id: str, **updates) -> APIProfile:
        """
        Update API profile.
        
        Args:
            profile_id: Profile to update
            **updates: Fields to update
            
        Returns:
            Updated APIProfile
            
        Raises:
            ValueError: If profile not found
        """
        if profile_id not in self.profiles:
            raise ValueError(f"Profile {profile_id} not found")
        
        profile = self.profiles[profile_id]
        
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.updated_at = datetime.now()
        self._save_profile(profile)
        
        logger.info(f"Updated API profile: {profile_id}")
        
        return profile
    
    def delete_profile(self, profile_id: str):
        """
        Delete API profile.
        
        Args:
            profile_id: Profile to delete
            
        Raises:
            ValueError: If profile not found
        """
        if profile_id not in self.profiles:
            raise ValueError(f"Profile {profile_id} not found")
        
        # Close client if exists
        if profile_id in self.clients:
            # Client cleanup would go here
            del self.clients[profile_id]
        
        del self.profiles[profile_id]
        
        # Delete file
        profile_file = self.storage_path / f"{profile_id}.json"
        if profile_file.exists():
            profile_file.unlink()
        
        logger.info(f"Deleted API profile: {profile_id}")
    
    def get_profile(self, profile_id: str) -> Optional[APIProfile]:
        """
        Get API profile by ID.
        
        Args:
            profile_id: Profile identifier
            
        Returns:
            APIProfile or None if not found
        """
        return self.profiles.get(profile_id)
    
    def list_profiles(self) -> List[APIProfile]:
        """List all API profiles."""
        return list(self.profiles.values())
    
    def add_endpoint(
        self,
        profile_id: str,
        endpoint_id: str,
        path: str,
        methods: List[HTTPMethod],
        **kwargs
    ) -> APIEndpoint:
        """
        Add endpoint to API profile.
        
        Args:
            profile_id: Profile to add endpoint to
            endpoint_id: Unique endpoint identifier
            path: Endpoint path
            methods: Allowed HTTP methods
            **kwargs: Additional endpoint settings
            
        Returns:
            Created APIEndpoint
            
        Raises:
            ValueError: If profile not found
        """
        if profile_id not in self.profiles:
            raise ValueError(f"Profile {profile_id} not found")
        
        profile = self.profiles[profile_id]
        
        endpoint = APIEndpoint(
            path=path,
            methods=set(methods),
            **kwargs
        )
        
        profile.endpoints[endpoint_id] = endpoint
        profile.updated_at = datetime.now()
        self._save_profile(profile)
        
        logger.info(f"Added endpoint {endpoint_id} to profile {profile_id}")
        
        return endpoint
    
    async def _get_client(self, profile_id: str) -> HTTPClientWithCaching:
        """Get or create HTTP client for profile."""
        if profile_id not in self.clients:
            profile = self.profiles.get(profile_id)
            if not profile:
                raise ValueError(f"Profile {profile_id} not found")
            
            # Create client config
            config = HTTPClientConfig(
                timeout=profile.timeout,
                verify_ssl=profile.verify_ssl,
                rate_limit_per_second=profile.rate_limit_per_minute / 60.0
            )
            
            # Add authentication headers
            if profile.auth_config:
                auth = profile.auth_config
                if auth.auth_type == AuthType.API_KEY and auth.api_key:
                    config.default_headers[auth.api_key_header] = auth.api_key
                elif auth.auth_type == AuthType.BEARER_TOKEN and auth.bearer_token:
                    config.default_headers['Authorization'] = f"Bearer {auth.bearer_token}"
                elif auth.auth_type == AuthType.CUSTOM:
                    config.default_headers.update(auth.custom_headers)
            
            # Create Guardian policy for this API
            policy = NetworkPolicy(
                name=f"api_{profile_id}",
                description=f"Policy for {profile.name}",
                allowed_operations=profile.allowed_operations or set(OperationType),
                enable_logging=True
            )
            
            # Create client with custom guardian
            guardian = Guardian(policy)
            client = HTTPClientWithCaching(config=config, guardian=guardian)
            
            self.clients[profile_id] = client
        
        return self.clients[profile_id]
    
    async def call(
        self,
        profile_id: str,
        endpoint_id: str,
        method: HTTPMethod = HTTPMethod.GET,
        **kwargs
    ) -> Any:
        """
        Make API call to configured endpoint.
        
        Args:
            profile_id: API profile to use
            endpoint_id: Endpoint identifier
            method: HTTP method
            **kwargs: Additional request parameters
            
        Returns:
            API response
            
        Raises:
            ValueError: If profile or endpoint not found
            PermissionError: If operation not allowed
        """
        import time
        start_time = time.time()
        
        # Get profile
        profile = self.profiles.get(profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")
        
        if not profile.enabled:
            raise PermissionError(f"Profile {profile_id} is disabled")
        
        # Get endpoint
        endpoint = profile.endpoints.get(endpoint_id)
        if not endpoint:
            raise ValueError(f"Endpoint {endpoint_id} not found in profile {profile_id}")
        
        # Check if method is allowed
        if method not in endpoint.methods:
            raise PermissionError(
                f"Method {method.value} not allowed for endpoint {endpoint_id}"
            )
        
        # Build full URL
        url = f"{profile.base_url.rstrip('/')}/{endpoint.path.lstrip('/')}"
        
        log_entry = APICallLog(
            profile_id=profile_id,
            endpoint=endpoint_id,
            method=method.value
        )
        
        try:
            # Get client
            client = await self._get_client(profile_id)
            
            # Make request
            response = await client.request(
                method.value,
                url,
                cache_ttl=endpoint.cache_ttl,
                **kwargs
            )
            
            log_entry.status_code = response.status_code
            log_entry.success = 200 <= response.status_code < 300
            log_entry.request_time = time.time() - start_time
            
            logger.info(
                f"API call: {profile_id}.{endpoint_id} [{response.status_code}] "
                f"in {log_entry.request_time:.2f}s"
            )
            
            self.call_logs.append(log_entry)
            
            return response.content
        
        except Exception as e:
            log_entry.error = str(e)
            log_entry.request_time = time.time() - start_time
            self.call_logs.append(log_entry)
            
            logger.error(f"API call failed: {profile_id}.{endpoint_id} - {e}")
            raise
    
    def get_call_logs(
        self,
        profile_id: Optional[str] = None,
        limit: int = 100
    ) -> List[APICallLog]:
        """
        Get API call logs.
        
        Args:
            profile_id: Filter by profile (optional)
            limit: Maximum number of logs to return
            
        Returns:
            List of APICallLog entries
        """
        logs = self.call_logs
        
        if profile_id:
            logs = [log for log in logs if log.profile_id == profile_id]
        
        return logs[-limit:]
    
    def get_stats(self, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get API usage statistics.
        
        Args:
            profile_id: Filter by profile (optional)
            
        Returns:
            Statistics dictionary
        """
        logs = self.get_call_logs(profile_id)
        
        if not logs:
            return {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "success_rate": 0.0,
                "avg_request_time": 0.0
            }
        
        successful = [log for log in logs if log.success]
        failed = [log for log in logs if not log.success]
        
        avg_time = sum(log.request_time for log in logs) / len(logs)
        
        return {
            "total_calls": len(logs),
            "successful_calls": len(successful),
            "failed_calls": len(failed),
            "success_rate": len(successful) / len(logs) if logs else 0.0,
            "avg_request_time": avg_time,
            "profiles": len(self.profiles),
        }
    
    async def close_all(self):
        """Close all HTTP clients."""
        for client in self.clients.values():
            await client.close()
        self.clients.clear()
        logger.info("All API clients closed")
