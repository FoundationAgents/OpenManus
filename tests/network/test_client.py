"""Tests for HTTP client with caching."""

import pytest
import httpx
from unittest.mock import AsyncMock, Mock, patch
from app.network.client import HTTPClientWithCaching, HTTPClientConfig
from app.network.guardian import Guardian, NetworkPolicy, OperationType


@pytest.fixture
def permissive_guardian():
    """Guardian that allows all operations."""
    policy = NetworkPolicy(
        name="permissive",
        description="Allow all",
        allowed_operations=set(OperationType),
        blocked_hosts=[],
        blocked_ports=[]
    )
    return Guardian(policy)


@pytest.fixture
def client_config():
    """HTTP client configuration."""
    return HTTPClientConfig(
        enable_cache=True,
        cache_max_size=100,
        cache_default_ttl=60,
        timeout=10.0,
        enable_rate_limiting=False,  # Disable for faster tests
        verify_ssl=False
    )


@pytest.mark.asyncio
async def test_client_initialization(client_config, permissive_guardian):
    """Test client initialization."""
    client = HTTPClientWithCaching(config=client_config, guardian=permissive_guardian)
    assert client.config.enable_cache is True
    assert client.cache is not None


@pytest.mark.asyncio
async def test_client_get_request(client_config, permissive_guardian):
    """Test GET request."""
    client = HTTPClientWithCaching(config=client_config, guardian=permissive_guardian)
    
    # Mock httpx response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"message": "success"}'
    mock_response.json.return_value = {"message": "success"}
    mock_response.url = "http://example.com"
    mock_response.raise_for_status = Mock()
    
    with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        response = await client.get("http://example.com")
        
        assert response.status_code == 200
        assert response.content == {"message": "success"}
        assert response.from_cache is False


@pytest.mark.asyncio
async def test_client_caching(client_config, permissive_guardian):
    """Test response caching."""
    client = HTTPClientWithCaching(config=client_config, guardian=permissive_guardian)
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"message": "success"}'
    mock_response.json.return_value = {"message": "success"}
    mock_response.url = "http://example.com"
    mock_response.raise_for_status = Mock()
    
    with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        # First request - should hit the network
        response1 = await client.get("http://example.com")
        assert response1.from_cache is False
        assert mock_request.call_count == 1
        
        # Second request - should be cached
        response2 = await client.get("http://example.com")
        assert response2.from_cache is True
        assert mock_request.call_count == 1  # No additional network call


@pytest.mark.asyncio
async def test_client_post_not_cached(client_config, permissive_guardian):
    """Test that POST requests are not cached."""
    # Need to allow POST in policy
    policy = NetworkPolicy(
        name="permissive",
        description="Allow all",
        allowed_operations=set(OperationType),
        require_confirmation=[]  # Don't require confirmation for testing
    )
    guardian = Guardian(policy)
    
    client = HTTPClientWithCaching(config=client_config, guardian=guardian)
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"message": "created"}'
    mock_response.json.return_value = {"message": "created"}
    mock_response.url = "http://example.com"
    mock_response.raise_for_status = Mock()
    
    with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        # First POST
        response1 = await client.post("http://example.com", json={"data": "test"})
        assert response1.from_cache is False
        
        # Second POST - should also hit network (no caching)
        response2 = await client.post("http://example.com", json={"data": "test"})
        assert response2.from_cache is False
        assert mock_request.call_count == 2


@pytest.mark.asyncio
async def test_client_guardian_blocking(client_config):
    """Test Guardian blocking requests."""
    # Create restrictive policy
    policy = NetworkPolicy(
        name="restrictive",
        description="Block all",
        allowed_operations=set(),  # Empty set - block all
        blocked_hosts=["example.com"]
    )
    guardian = Guardian(policy)
    
    client = HTTPClientWithCaching(config=client_config, guardian=guardian)
    
    # Should be blocked by Guardian
    with pytest.raises(PermissionError):
        await client.get("http://example.com")


@pytest.mark.asyncio
async def test_client_cache_invalidation(client_config, permissive_guardian):
    """Test cache invalidation."""
    client = HTTPClientWithCaching(config=client_config, guardian=permissive_guardian)
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"message": "success"}'
    mock_response.json.return_value = {"message": "success"}
    mock_response.url = "http://example.com"
    mock_response.raise_for_status = Mock()
    
    with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        # First request - cache it
        await client.get("http://example.com")
        assert mock_request.call_count == 1
        
        # Invalidate cache
        client.invalidate_cache("http://example.com")
        
        # Next request should hit network again
        await client.get("http://example.com")
        assert mock_request.call_count == 2


@pytest.mark.asyncio
async def test_client_cache_stats(client_config, permissive_guardian):
    """Test getting cache statistics."""
    client = HTTPClientWithCaching(config=client_config, guardian=permissive_guardian)
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.text = "success"
    mock_response.url = "http://example.com"
    mock_response.raise_for_status = Mock()
    
    with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        # Make some requests
        await client.get("http://example.com/1")
        await client.get("http://example.com/1")  # Cache hit
        await client.get("http://example.com/2")
        
        stats = client.get_cache_stats()
        
        assert "hits" in stats
        assert "misses" in stats
        assert "entry_count" in stats


@pytest.mark.asyncio
async def test_client_custom_cache_ttl(client_config, permissive_guardian):
    """Test custom cache TTL."""
    client = HTTPClientWithCaching(config=client_config, guardian=permissive_guardian)
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.text = "success"
    mock_response.url = "http://example.com"
    mock_response.raise_for_status = Mock()
    
    with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        # Request with custom TTL
        await client.get("http://example.com", cache_ttl=120)
        
        # Should be cached
        response = await client.get("http://example.com")
        assert response.from_cache is True


@pytest.mark.asyncio
async def test_client_context_manager(client_config, permissive_guardian):
    """Test client as context manager."""
    async with HTTPClientWithCaching(config=client_config, guardian=permissive_guardian) as client:
        assert client is not None
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.text = "success"
        mock_response.url = "http://example.com"
        mock_response.raise_for_status = Mock()
        
        with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            response = await client.get("http://example.com")
            assert response.status_code == 200
    
    # Client should be closed after context


@pytest.mark.asyncio
async def test_client_without_cache(permissive_guardian):
    """Test client with caching disabled."""
    config = HTTPClientConfig(
        enable_cache=False,
        timeout=10.0,
        enable_rate_limiting=False
    )
    
    client = HTTPClientWithCaching(config=config, guardian=permissive_guardian)
    assert client.cache is None
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.text = "success"
    mock_response.url = "http://example.com"
    mock_response.raise_for_status = Mock()
    
    with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        # Both requests should hit network
        await client.get("http://example.com")
        await client.get("http://example.com")
        
        assert mock_request.call_count == 2
