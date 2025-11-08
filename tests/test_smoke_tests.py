"""
Smoke Tests for Critical System Components

Fast, basic validation tests for:
- MCP tool access
- Network client operations with caching
- Backup/restore cycle
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock


pytestmark = pytest.mark.smoke


class TestMCPToolAccess:
    """Smoke tests for MCP tool access."""
    
    @pytest.mark.asyncio
    async def test_file_read_tool_access(self, mock_mcp_tools):
        """Test basic file_read tool access."""
        result = await mock_mcp_tools["file_read"]()
        
        assert result is not None
        assert "content" in result
    
    @pytest.mark.asyncio
    async def test_file_write_tool_access(self, mock_mcp_tools):
        """Test basic file_write tool access."""
        result = await mock_mcp_tools["file_write"]()
        
        assert result is not None
        assert "status" in result
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_execute_command_tool_access(self, mock_mcp_tools):
        """Test execute_command tool access."""
        result = await mock_mcp_tools["execute_command"]()
        
        assert result is not None
        assert "output" in result
    
    @pytest.mark.asyncio
    async def test_search_tool_access(self, mock_mcp_tools):
        """Test search tool access."""
        result = await mock_mcp_tools["search"]()
        
        assert result is not None
        assert "results" in result
    
    @pytest.mark.asyncio
    async def test_list_directory_tool_access(self, mock_mcp_tools):
        """Test list_directory tool access."""
        result = await mock_mcp_tools["list_directory"]()
        
        assert result is not None
        assert "files" in result
    
    @pytest.mark.asyncio
    async def test_all_tools_accessible(self, mock_mcp_tools):
        """Test all MCP tools are accessible."""
        tool_names = ["file_read", "file_write", "execute_command", "search", "list_directory"]
        
        for tool_name in tool_names:
            assert tool_name in mock_mcp_tools
            tool = mock_mcp_tools[tool_name]
            assert callable(tool) or isinstance(tool, AsyncMock)


class TestNetworkClientOperations:
    """Smoke tests for network client operations with caching."""
    
    @pytest.mark.asyncio
    async def test_basic_http_request(self, mock_network_client):
        """Test basic HTTP request."""
        result = await mock_network_client.request("http://example.com")
        
        assert result is not None
        assert result["status"] == 200
    
    @pytest.mark.asyncio
    async def test_request_caching(self, mock_network_client):
        """Test that requests are cached."""
        url = "http://example.com/api"
        
        # First request
        result1 = await mock_network_client.request(url)
        
        # Second request (should be cached)
        result2 = await mock_network_client.request(url)
        
        # Results should be identical
        assert result1 == result2
        
        # Cache should have the entry
        assert f"GET:{url}" in mock_network_client.cache
    
    @pytest.mark.asyncio
    async def test_different_methods_not_cached_together(self, mock_network_client):
        """Test that different HTTP methods are cached separately."""
        url = "http://example.com/data"
        
        # Make GET request
        result_get = await mock_network_client.request(url, method="GET")
        
        # Make POST request
        result_post = await mock_network_client.request(url, method="POST")
        
        # Should have different cache entries
        assert "GET:" + url in mock_network_client.cache
        assert "POST:" + url in mock_network_client.cache
    
    @pytest.mark.asyncio
    async def test_cache_clear(self, mock_network_client):
        """Test clearing the cache."""
        # Add to cache
        await mock_network_client.request("http://example.com")
        assert len(mock_network_client.cache) > 0
        
        # Clear cache
        mock_network_client.clear_cache()
        
        assert len(mock_network_client.cache) == 0
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests(self, mock_network_client):
        """Test multiple concurrent network requests."""
        urls = [
            "http://example.com/1",
            "http://example.com/2",
            "http://example.com/3"
        ]
        
        # Make concurrent requests
        results = await asyncio.gather(*[
            mock_network_client.request(url)
            for url in urls
        ])
        
        assert len(results) == 3
        assert all(r["status"] == 200 for r in results)
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate(self, mock_network_client):
        """Test cache hit rate calculation."""
        url = "http://example.com/api"
        
        # Make multiple requests
        for _ in range(5):
            await mock_network_client.request(url)
        
        # First request is a miss, rest are hits = 80% hit rate
        assert len(mock_network_client.cache) == 1


class TestBackupRestoreCycle:
    """Smoke tests for backup and restore operations."""
    
    @pytest.mark.asyncio
    async def test_create_basic_backup(self, mock_backup_manager):
        """Test creating a basic backup."""
        test_data = {"key": "value", "status": "ok"}
        
        backup_id = await mock_backup_manager.create_backup("test_backup", test_data)
        
        assert backup_id is not None
        assert backup_id.startswith("bak_")
    
    @pytest.mark.asyncio
    async def test_restore_from_backup(self, mock_backup_manager):
        """Test restoring from a backup."""
        test_data = {"important": "data"}
        
        # Create backup
        backup_id = await mock_backup_manager.create_backup("backup_1", test_data)
        
        # Restore from backup
        result = await mock_backup_manager.restore_backup(backup_id)
        
        assert result["status"] == "success"
        assert result["restored_data"] == test_data
    
    @pytest.mark.asyncio
    async def test_restore_nonexistent_backup(self, mock_backup_manager):
        """Test restoring from non-existent backup."""
        result = await mock_backup_manager.restore_backup("bak_999")
        
        assert result["status"] == "error"
        assert "reason" in result
    
    @pytest.mark.asyncio
    async def test_list_all_backups(self, mock_backup_manager):
        """Test listing all available backups."""
        # Create multiple backups
        data1 = {"type": "config"}
        data2 = {"type": "database"}
        
        await mock_backup_manager.create_backup("backup_1", data1)
        await mock_backup_manager.create_backup("backup_2", data2)
        
        # List backups
        backups = await mock_backup_manager.list_backups()
        
        assert len(backups) >= 2
        assert all("id" in b and "name" in b for b in backups)
    
    @pytest.mark.asyncio
    async def test_backup_restore_cycle(self, mock_backup_manager):
        """Test complete backup and restore cycle."""
        original_data = {
            "config": {"version": "1.0"},
            "state": {"initialized": True}
        }
        
        # Create backup
        backup_id = await mock_backup_manager.create_backup("cycle_test", original_data)
        assert backup_id is not None
        
        # Simulate data modification
        modified_data = {
            "config": {"version": "2.0"},
            "state": {"initialized": False}
        }
        
        # Restore from backup
        restore_result = await mock_backup_manager.restore_backup(backup_id)
        assert restore_result["status"] == "success"
        assert restore_result["restored_data"] == original_data
    
    @pytest.mark.asyncio
    async def test_multiple_backups_isolation(self, mock_backup_manager):
        """Test that multiple backups are isolated."""
        data1 = {"type": "backup_1", "value": 100}
        data2 = {"type": "backup_2", "value": 200}
        
        # Create two backups with different data
        backup_id_1 = await mock_backup_manager.create_backup("backup_1", data1)
        backup_id_2 = await mock_backup_manager.create_backup("backup_2", data2)
        
        # Verify isolation
        backups = await mock_backup_manager.list_backups()
        backup_1 = next(b for b in backups if b["id"] == backup_id_1)
        backup_2 = next(b for b in backups if b["id"] == backup_id_2)
        
        assert backup_1["data"]["type"] == "backup_1"
        assert backup_2["data"]["type"] == "backup_2"
    
    @pytest.mark.asyncio
    async def test_backup_with_metadata(self, mock_backup_manager):
        """Test backup creation with metadata."""
        test_data = {"content": "test"}
        
        # Create backup with metadata
        backup_id = await mock_backup_manager.create_backup(
            "backup_with_meta",
            test_data
        )
        
        # Verify backup was created
        backups = await mock_backup_manager.list_backups()
        backup = next(b for b in backups if b["id"] == backup_id)
        
        assert backup["name"] == "backup_with_meta"
        assert "created_at" in backup


class TestCriticalPathSmoke:
    """Smoke tests for critical system paths."""
    
    @pytest.mark.asyncio
    async def test_system_initialization(self, test_config):
        """Test system can be initialized."""
        assert test_config["llm"]["default_model"] is not None
        assert test_config["guardian"]["enabled"] is True
        assert test_config["sandbox"]["enabled"] is True
    
    @pytest.mark.asyncio
    async def test_basic_workflow_execution(self, sample_workflow, mock_workflow_executor):
        """Test basic workflow can be executed."""
        result = await mock_workflow_executor.execute(sample_workflow)
        
        assert result is not None
        assert result["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_agent_pool_available(self, mock_agent_pool):
        """Test agent pool has available agents."""
        agent = mock_agent_pool.get_available_agent()
        
        assert agent is not None
        assert agent["status"] == "ready"
    
    @pytest.mark.asyncio
    async def test_memory_system_accessible(self, mock_memory_store):
        """Test memory system is accessible."""
        # Store data
        key = await mock_memory_store.store("test", {"value": "data"})
        
        # Retrieve data
        result = await mock_memory_store.retrieve(key)
        
        assert result is not None
        assert result["value"]["value"] == "data"
    
    @pytest.mark.asyncio
    async def test_sandbox_available(self, mock_sandbox):
        """Test sandbox environment is available."""
        result = await mock_sandbox.run_code("print('test')", language="python")
        
        assert result is not None
        assert result["status"] == "success"
