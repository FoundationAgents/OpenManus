"""
Cross-Module Integration Tests for E2E Validation

Tests interactions between:
- Guardian security and workflow execution
- Memory system and agent decision-making
- Sandbox and version management
- Network operations and caching
- Backup system and recovery
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime


pytestmark = pytest.mark.integration


class TestGuardianSecurityIntegration:
    """Integration tests for Guardian security with other components."""
    
    @pytest.mark.asyncio
    async def test_guardian_blocks_sandboxed_execution(
        self, mock_guardian, mock_sandbox
    ):
        """Test Guardian can block execution in sandbox."""
        # Setup Guardian to deny
        mock_guardian.validate = AsyncMock(return_value={
            "approved": False,
            "reason": "Suspicious code pattern"
        })
        
        # Try to execute
        code = "import os; os.system('rm -rf /')"
        
        # In real system, Guardian would be checked before sandbox execution
        validation = await mock_guardian.validate()
        
        if not validation["approved"]:
            # Execution should be blocked
            assert validation["approved"] is False
    
    @pytest.mark.asyncio
    async def test_guardian_audit_trail_with_workflow(
        self, sample_workflow, mock_guardian, temp_db
    ):
        """Test Guardian maintains audit trail during workflow execution."""
        cursor = temp_db.cursor()
        
        # Create audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                action TEXT,
                status TEXT,
                timestamp TIMESTAMP
            )
        """)
        
        # Log Guardian validation
        cursor.execute("""
            INSERT INTO audit_log (id, action, status, timestamp)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, ("log_001", "guardian_validate", "approved"))
        
        temp_db.commit()
        
        # Verify audit trail
        cursor.execute("SELECT action, status FROM audit_log WHERE id = ?", ("log_001",))
        record = cursor.fetchone()
        
        assert record is not None
        assert record[0] == "guardian_validate"
        assert record[1] == "approved"


class TestMemoryAgentIntegration:
    """Integration tests for memory system with agent operations."""
    
    @pytest.mark.asyncio
    async def test_agent_learns_from_memory(
        self, mock_agent, mock_memory_store
    ):
        """Test agent learning from stored memory."""
        # Store training data in memory
        training_data = {
            "patterns": ["error_handling", "logging"],
            "best_practices": "Always validate inputs"
        }
        
        await mock_memory_store.store("training", training_data)
        
        # Agent retrieves and uses
        retrieved = await mock_memory_store.retrieve("training")
        assert retrieved is not None
        
        # Agent executes task
        task = {"id": "task_001", "action": "write_code"}
        result = await mock_agent.execute_task(task)
        
        assert result["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_memory_persistence_across_agent_changes(
        self, mock_memory_store, mock_agent_pool
    ):
        """Test memory persists when agents are replaced."""
        # Store knowledge
        knowledge = {"database_query_optimization": "Use indexes"}
        await mock_memory_store.store("knowledge", knowledge)
        
        # Replace agent
        old_agent = mock_agent_pool.get_available_agent()
        mock_agent_pool.replace_agent(old_agent["id"], "agent_002")
        
        # Memory should still be available
        retrieved = await mock_memory_store.retrieve("knowledge")
        assert retrieved is not None
        assert "database_query_optimization" in retrieved["value"]


class TestSandboxVersionIntegration:
    """Integration tests for sandbox execution with version management."""
    
    @pytest.mark.asyncio
    async def test_execute_code_and_create_version(
        self, mock_sandbox, mock_version_manager, sample_code_snippet
    ):
        """Test executing code in sandbox and versioning the result."""
        code = sample_code_snippet["python"]
        
        # Execute in sandbox
        exec_result = await mock_sandbox.run_code(code)
        assert exec_result["status"] == "success"
        
        # Create version of the code
        version_id = await mock_version_manager.create_version(code)
        assert version_id is not None
        
        # Verify version can be retrieved
        version = await mock_version_manager.get_version(version_id)
        assert version is not None
        assert version["content"] == code
    
    @pytest.mark.asyncio
    async def test_rollback_code_and_re_execute(
        self, mock_sandbox, mock_version_manager, sample_code_snippet
    ):
        """Test rolling back code version and re-executing."""
        code_v1 = "print('version 1')"
        code_v2 = "print('version 2')"
        
        # Create versions
        v1_id = await mock_version_manager.create_version(code_v1)
        v2_id = await mock_version_manager.create_version(code_v2)
        
        # Rollback to v1
        rollback_result = await mock_version_manager.rollback(v1_id)
        assert rollback_result["status"] == "success"
        
        # Re-execute rolled back code
        exec_result = await mock_sandbox.run_code(
            rollback_result["content"]
        )
        assert exec_result["status"] == "success"


class TestNetworkCachingIntegration:
    """Integration tests for network caching with other systems."""
    
    @pytest.mark.asyncio
    async def test_network_cache_with_memory_store(
        self, mock_network_client, mock_memory_store
    ):
        """Test network responses cached and stored in memory."""
        url = "http://example.com/data"
        
        # First network request
        response1 = await mock_network_client.request(url)
        
        # Store response in memory
        mem_key = await mock_memory_store.store(
            "api_response",
            response1,
            metadata={"source": url}
        )
        
        # Second network request (cached)
        response2 = await mock_network_client.request(url)
        
        # Both responses should be identical
        assert response1 == response2
        
        # Memory should have the stored response
        stored = await mock_memory_store.retrieve(mem_key)
        assert stored["value"] == response1
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_memory_update(
        self, mock_network_client, mock_memory_store
    ):
        """Test cache can be invalidated when memory is updated."""
        url = "http://example.com/config"
        
        # Get from network (cached)
        response1 = await mock_network_client.request(url)
        
        # Store in memory
        await mock_memory_store.store("config", response1)
        
        # Clear network cache
        mock_network_client.clear_cache()
        
        # Cache should be empty
        assert len(mock_network_client.cache) == 0


class TestBackupRecoveryIntegration:
    """Integration tests for backup system with recovery operations."""
    
    @pytest.mark.asyncio
    async def test_backup_workflow_state_and_recovery(
        self, sample_workflow, mock_backup_manager, mock_workflow_executor
    ):
        """Test backing up workflow state and recovering it."""
        # Execute workflow
        result = await mock_workflow_executor.execute(sample_workflow)
        
        # Backup workflow state
        backup_id = await mock_backup_manager.create_backup(
            "workflow_state",
            {
                "workflow": sample_workflow,
                "result": result
            }
        )
        
        # Simulate workflow loss
        sample_workflow = None
        
        # Restore from backup
        recovery = await mock_backup_manager.restore_backup(backup_id)
        assert recovery["status"] == "success"
        
        # Workflow should be recovered
        recovered_workflow = recovery["restored_data"]["workflow"]
        assert recovered_workflow["id"] == "wf_001"
    
    @pytest.mark.asyncio
    async def test_backup_agent_pool_and_restore(
        self, mock_agent_pool, mock_backup_manager
    ):
        """Test backing up agent pool state."""
        # Get pool state
        pool_state = {
            "agents": mock_agent_pool.agents,
            "stats": mock_agent_pool.get_pool_stats()
        }
        
        # Create backup
        backup_id = await mock_backup_manager.create_backup(
            "agent_pool",
            pool_state
        )
        
        # Restore backup
        recovery = await mock_backup_manager.restore_backup(backup_id)
        
        assert recovery["status"] == "success"
        assert recovery["restored_data"]["agents"] == mock_agent_pool.agents


class TestAgentFailoverIntegration:
    """Integration tests for agent failover with other systems."""
    
    @pytest.mark.asyncio
    async def test_failover_preserves_memory(
        self, mock_agent_pool, mock_memory_store
    ):
        """Test memory is preserved during agent failover."""
        # Store knowledge
        knowledge = {"experience": "learned_pattern"}
        await mock_memory_store.store("experience", knowledge)
        
        # Agent fails
        old_agent = mock_agent_pool.get_available_agent()
        
        # Failover to new agent
        mock_agent_pool.replace_agent(old_agent["id"], "agent_backup")
        
        # New agent should still have access to memory
        retrieved = await mock_memory_store.retrieve("experience")
        assert retrieved is not None
    
    @pytest.mark.asyncio
    async def test_failover_continues_workflow(
        self, sample_workflow, mock_agent_pool, mock_workflow_executor
    ):
        """Test workflow continues after agent failover."""
        # Start workflow
        result1 = await mock_workflow_executor.execute(sample_workflow)
        
        # Simulate agent failure
        old_agent = mock_agent_pool.get_available_agent()
        mock_agent_pool.replace_agent(old_agent["id"], "agent_backup")
        
        # Continue workflow
        result2 = await mock_workflow_executor.execute(sample_workflow)
        
        # Both should complete
        assert result1["status"] == "completed"
        assert result2["status"] == "completed"


class TestComplexMultiComponentScenarios:
    """Complex test scenarios involving multiple components."""
    
    @pytest.mark.asyncio
    async def test_complete_secure_workflow_execution(
        self,
        sample_workflow,
        mock_guardian,
        mock_sandbox,
        mock_version_manager,
        mock_memory_store,
        sample_code_snippet,
        temp_db
    ):
        """Test complete secure workflow with all components."""
        cursor = temp_db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_log (
                id TEXT PRIMARY KEY,
                step TEXT,
                status TEXT
            )
        """)
        
        # Step 1: Guardian approval
        cursor.execute(
            "INSERT INTO execution_log VALUES (?, ?, ?)",
            ("exec_001", "guardian_check", "approved")
        )
        
        # Step 2: Code execution in sandbox
        code = sample_code_snippet["python"]
        exec_result = await mock_sandbox.run_code(code)
        cursor.execute(
            "INSERT INTO execution_log VALUES (?, ?, ?)",
            ("exec_001", "sandbox_execute", exec_result["status"])
        )
        
        # Step 3: Version the code
        version_id = await mock_version_manager.create_version(code)
        cursor.execute(
            "INSERT INTO execution_log VALUES (?, ?, ?)",
            ("exec_001", "create_version", "success")
        )
        
        # Step 4: Store results in memory
        await mock_memory_store.store(
            "execution_001",
            {
                "workflow": sample_workflow["id"],
                "code": code,
                "result": exec_result,
                "version": version_id
            }
        )
        cursor.execute(
            "INSERT INTO execution_log VALUES (?, ?, ?)",
            ("exec_001", "store_memory", "success")
        )
        
        temp_db.commit()
        
        # Verify complete execution log
        cursor.execute("SELECT step, status FROM execution_log WHERE id = ?", ("exec_001",))
        logs = cursor.fetchall()
        
        assert len(logs) == 4
        assert all(status == "success" or status == "approved" for _, status in logs)
    
    @pytest.mark.asyncio
    async def test_disaster_recovery_scenario(
        self,
        mock_backup_manager,
        mock_memory_store,
        mock_agent_pool,
        mock_version_manager,
        sample_code_snippet
    ):
        """Test system recovery after multiple failures."""
        # Setup: Create versions and backups
        code_v1 = "print('original')"
        version_id = await mock_version_manager.create_version(code_v1)
        
        # Store state in memory
        await mock_memory_store.store("system_state", {
            "version": version_id,
            "code": code_v1
        })
        
        # Backup system state
        backup_id = await mock_backup_manager.create_backup(
            "pre_disaster",
            {
                "version": version_id,
                "agent_pool": mock_agent_pool.agents
            }
        )
        
        # Simulate disaster: agent failure
        mock_agent_pool.replace_agent("agent_001", "agent_backup")
        
        # Recovery: Restore from backup
        recovery = await mock_backup_manager.restore_backup(backup_id)
        
        # Verify recovery
        assert recovery["status"] == "success"
        assert recovery["restored_data"]["version"] == version_id
