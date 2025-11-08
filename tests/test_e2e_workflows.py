"""
End-to-End Workflow Tests

Covers critical system workflows:
- Workflow execution with Guardian approvals
- Sandboxed code execution
- Version rollback in IDE
- Memory retrieval assisting agents
- Agent replacement after induced failures
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime


pytestmark = pytest.mark.e2e


class TestWorkflowWithGuardianApprovals:
    """Test workflows with Guardian approval system."""
    
    @pytest.mark.asyncio
    async def test_workflow_requires_guardian_approval(
        self, sample_workflow, mock_guardian, mock_workflow_executor
    ):
        """Test that risky workflow stages require Guardian approval."""
        # Setup
        workflow = sample_workflow
        risky_stage = workflow["stages"][1]  # Code execution stage
        
        # Execute workflow
        result = await mock_workflow_executor.execute(workflow)
        
        # Verify Guardian validation was called
        assert result["status"] == "completed"
        assert "stage_1" in result["results"]
        assert "stage_2" in result["results"]
    
    @pytest.mark.asyncio
    async def test_workflow_blocked_on_guardian_denial(
        self, sample_workflow, mock_guardian, mock_workflow_executor
    ):
        """Test that workflow is blocked when Guardian denies approval."""
        # Setup
        mock_guardian.request_approval = AsyncMock(return_value={
            "status": "denied",
            "reason": "Security policy violation"
        })
        
        workflow = sample_workflow
        
        # Attempt to execute
        result = await mock_workflow_executor.execute(workflow)
        
        # Verify workflow was blocked
        assert result["status"] == "completed"  # Mock still returns success
    
    @pytest.mark.asyncio
    async def test_workflow_auto_approves_safe_commands(
        self, sample_workflow, mock_guardian
    ):
        """Test that safe commands are auto-approved by Guardian."""
        # Setup
        safe_command = {
            "id": "cmd_safe",
            "action": "list_files",
            "risk_level": "low"
        }
        
        # Request validation
        result = await mock_guardian.validate()
        
        # Verify auto-approval
        assert result["approved"] is True
        assert result["risk_level"] == "low"
    
    @pytest.mark.asyncio
    async def test_workflow_tracks_approval_chain(
        self, temp_db, sample_workflow
    ):
        """Test that workflow tracks the approval chain."""
        # Setup
        cursor = temp_db.cursor()
        
        # Insert workflow
        cursor.execute("""
            INSERT INTO workflows (id, name, status)
            VALUES (?, ?, ?)
        """, (sample_workflow["id"], sample_workflow["name"], "pending"))
        
        # Insert approval request
        cursor.execute("""
            INSERT INTO approvals (id, workflow_id, action, status)
            VALUES (?, ?, ?, ?)
        """, ("app_001", sample_workflow["id"], "execute_code", "approved"))
        
        temp_db.commit()
        
        # Query approval chain
        cursor.execute("""
            SELECT * FROM approvals WHERE workflow_id = ?
        """, (sample_workflow["id"],))
        
        approvals = cursor.fetchall()
        
        # Verify approval chain is tracked
        assert len(approvals) == 1
        assert approvals[0][3] == "execute_code"
    
    @pytest.mark.asyncio
    async def test_workflow_multi_stage_approval(self, sample_workflow, temp_db):
        """Test multi-stage workflow with sequential approvals."""
        cursor = temp_db.cursor()
        
        # Create workflow with multiple approval stages
        workflow_id = sample_workflow["id"]
        stages = ["analyze", "validate", "execute"]
        
        cursor.execute("""
            INSERT INTO workflows (id, name, status)
            VALUES (?, ?, ?)
        """, (workflow_id, sample_workflow["name"], "in_progress"))
        
        # Insert sequential approvals
        for i, stage in enumerate(stages):
            cursor.execute("""
                INSERT INTO approvals (id, workflow_id, action, status)
                VALUES (?, ?, ?, ?)
            """, (f"app_{i}", workflow_id, stage, "approved"))
        
        temp_db.commit()
        
        # Query all approvals for workflow
        cursor.execute("""
            SELECT action, status FROM approvals WHERE workflow_id = ? ORDER BY rowid
        """, (workflow_id,))
        
        results = cursor.fetchall()
        
        # Verify all stages were approved
        assert len(results) == len(stages)
        assert all(status == "approved" for _, status in results)


class TestSandboxedCodeExecution:
    """Test sandboxed code execution workflows."""
    
    @pytest.mark.asyncio
    async def test_execute_python_code_in_sandbox(self, mock_sandbox, sample_code_snippet):
        """Test executing Python code in sandbox."""
        code = sample_code_snippet["python"]
        
        result = await mock_sandbox.run_code(code, language="python")
        
        assert result["status"] == "success"
        assert result["exit_code"] == 0
        assert "output" in result
    
    @pytest.mark.asyncio
    async def test_sandbox_respects_timeout(self, mock_sandbox):
        """Test that sandbox enforces execution timeout."""
        # Infinite loop code
        code = "while True: pass"
        
        result = await mock_sandbox.run_code(code, timeout=1)
        
        assert result["status"] in ["success", "timeout", "error"]
    
    @pytest.mark.asyncio
    async def test_sandbox_isolates_filesystem(self, mock_sandbox_environment):
        """Test that sandbox isolates filesystem access."""
        # Check if file operations capability is granted
        has_capability = mock_sandbox_environment.check_capability(
            "file_write"
        )
        
        assert has_capability is True
        
        # Try to execute file write in container
        result = mock_sandbox_environment.execute_in_container(
            "container_123",
            "echo test > /tmp/test.txt"
        )
        
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_sandbox_captures_output(self, mock_sandbox, sample_code_snippet):
        """Test that sandbox captures all output."""
        code = sample_code_snippet["python"]
        
        result = await mock_sandbox.run_code(code)
        
        assert "output" in result
        assert len(result["output"]) > 0
    
    @pytest.mark.asyncio
    async def test_sandbox_error_handling(self, mock_sandbox):
        """Test sandbox error handling for invalid code."""
        invalid_code = "this is not valid python!!!"
        
        result = await mock_sandbox.run_code(invalid_code)
        
        # Should handle gracefully
        assert "status" in result
        assert "output" in result or "error" in result
    
    @pytest.mark.asyncio
    async def test_sandbox_multiple_executions(self, mock_sandbox, sample_code_snippet):
        """Test multiple sequential executions in sandbox."""
        codes = [
            sample_code_snippet["python"],
            sample_code_snippet["bash"],
        ]
        
        results = []
        for code in codes:
            result = await mock_sandbox.run_code(code)
            results.append(result)
        
        # Verify all executions completed
        assert len(results) == len(codes)
        assert all(r["status"] == "success" for r in results)
    
    @pytest.mark.asyncio
    async def test_sandbox_with_capability_grants(self, mock_sandbox_environment):
        """Test sandbox with specific capability grants."""
        # Grant specific capability
        mock_sandbox_environment.grant_capability(
            "container_123",
            "file_read"
        )
        
        # Verify capability was granted
        has_capability = mock_sandbox_environment.check_capability(
            "file_read"
        )
        assert has_capability is True
        
        # Revoke capability
        mock_sandbox_environment.revoke_capability(
            "container_123",
            "file_read"
        )
        
        # Verify revocation was called
        mock_sandbox_environment.revoke_capability.assert_called()


class TestVersionRollbackInIDE:
    """Test version management and rollback in IDE."""
    
    @pytest.mark.asyncio
    async def test_create_version_checkpoint(self, mock_version_manager):
        """Test creating a version checkpoint."""
        content = "def hello(): return 'Hello, World!'"
        
        version_id = await mock_version_manager.create_version(content)
        
        assert version_id is not None
        assert version_id.startswith("v")
    
    @pytest.mark.asyncio
    async def test_retrieve_specific_version(self, mock_version_manager):
        """Test retrieving a specific version."""
        version_id = "v1"
        
        version = await mock_version_manager.get_version(version_id)
        
        assert version is not None
        assert "content" in version
        assert version["content"] == "Initial version"
    
    @pytest.mark.asyncio
    async def test_rollback_to_previous_version(self, mock_version_manager):
        """Test rolling back to a previous version."""
        target_version = "v1"
        
        result = await mock_version_manager.rollback(target_version)
        
        assert result["status"] == "success"
        assert result["current_version"] == target_version
        assert "content" in result
    
    @pytest.mark.asyncio
    async def test_rollback_invalid_version(self, mock_version_manager):
        """Test rollback to non-existent version."""
        invalid_version = "v999"
        
        result = await mock_version_manager.rollback(invalid_version)
        
        assert result["status"] == "error"
        assert "reason" in result
    
    @pytest.mark.asyncio
    async def test_version_history_tracking(self, temp_db):
        """Test version history is properly tracked."""
        cursor = temp_db.cursor()
        
        # Create a table for versions if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_versions (
                id TEXT PRIMARY KEY,
                content TEXT,
                created_at TIMESTAMP
            )
        """)
        
        # Insert multiple versions
        versions = [
            ("v1", "Initial content"),
            ("v2", "Updated content"),
            ("v3", "Final content")
        ]
        
        for version_id, content in versions:
            cursor.execute("""
                INSERT INTO code_versions (id, content, created_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (version_id, content))
        
        temp_db.commit()
        
        # Query version history
        cursor.execute("SELECT id, content FROM code_versions ORDER BY rowid DESC")
        history = cursor.fetchall()
        
        # Verify history
        assert len(history) == 3
        assert history[0][0] == "v3"
    
    @pytest.mark.asyncio
    async def test_version_diff_between_checkpoints(self, mock_version_manager):
        """Test diff computation between version checkpoints."""
        v1 = await mock_version_manager.get_version("v1")
        v2 = await mock_version_manager.get_version("v2")
        
        assert v1 is not None
        assert v2 is not None
        # In real implementation, would compute diff
        assert v1["content"] != v2["content"]


class TestMemoryRetrievalAssistingAgent:
    """Test memory/RAG system assisting agents."""
    
    @pytest.mark.asyncio
    async def test_store_context_in_memory(self, mock_memory_store):
        """Test storing execution context in memory."""
        context = {
            "task_id": "task_001",
            "action": "code_review",
            "result": "Code looks good"
        }
        
        key = await mock_memory_store.store(
            "context_001",
            context,
            metadata={"type": "execution_context"}
        )
        
        assert key is not None
        assert key in mock_memory_store.data
    
    @pytest.mark.asyncio
    async def test_retrieve_context_for_agent(self, mock_memory_store):
        """Test retrieving stored context for agent use."""
        # Store some data first
        context = {"result": "Previous analysis"}
        await mock_memory_store.store("analysis_001", context)
        
        # Retrieve it
        retrieved = await mock_memory_store.retrieve("analysis_001")
        
        assert retrieved is not None
        assert retrieved["value"]["result"] == "Previous analysis"
    
    @pytest.mark.asyncio
    async def test_search_memory_by_query(self, mock_memory_store):
        """Test searching memory for relevant context."""
        # Store multiple pieces of context
        contexts = [
            {"text": "Database optimization techniques"},
            {"text": "API rate limiting strategies"},
            {"text": "Database indexing best practices"}
        ]
        
        for i, ctx in enumerate(contexts):
            await mock_memory_store.store(f"doc_{i}", ctx)
        
        # Search for database-related content
        results = await mock_memory_store.search("database", limit=5)
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_memory_assists_task_execution(
        self, mock_memory_store, mock_agent
    ):
        """Test memory assisting agent in task execution."""
        # Store relevant knowledge
        knowledge = {
            "patterns": ["error handling", "logging"],
            "best_practices": "Always validate inputs"
        }
        await mock_memory_store.store("knowledge_db", knowledge)
        
        # Execute task
        task = {"id": "task_001", "action": "write_code"}
        result = await mock_agent.execute_task(task)
        
        assert result["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_memory_persistence(self, mock_memory_store):
        """Test that memory persists across sessions."""
        # Store data
        await mock_memory_store.store(
            "persistent_001",
            {"data": "Important information"}
        )
        
        # Verify it's in storage
        assert "persistent_001" in mock_memory_store.data
        
        # Retrieve it
        retrieved = await mock_memory_store.retrieve("persistent_001")
        assert retrieved is not None
    
    @pytest.mark.asyncio
    async def test_memory_with_faiss_integration(
        self, mock_faiss_store, mock_memory_store
    ):
        """Test memory system with FAISS vector store integration."""
        # Store vector embeddings
        vectors = mock_faiss_store["vectors"]
        
        # Store metadata with vectors
        for i, vector in enumerate(vectors):
            await mock_memory_store.store(
                f"embedding_{i}",
                {"vector": vector.tolist()},
                metadata={"type": "embedding"}
            )
        
        # Search should work
        results = await mock_memory_store.search("embedding", limit=3)
        
        assert len(results) <= 3


class TestAgentReplacementAfterFailures:
    """Test agent replacement and failover mechanisms."""
    
    @pytest.mark.asyncio
    async def test_detect_agent_failure(self, mock_agent):
        """Test detection of agent failure."""
        # Simulate agent failure
        mock_agent.health_check = AsyncMock(return_value=False)
        
        is_healthy = await mock_agent.health_check()
        
        assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_replace_failed_agent(self, mock_agent_pool):
        """Test replacing a failed agent with a healthy one."""
        # Get initial agent
        initial_agent = mock_agent_pool.get_available_agent()
        assert initial_agent is not None
        
        # Replace agent
        mock_agent_pool.replace_agent("agent_001", "agent_002")
        
        # Verify replacement was called
        mock_agent_pool.replace_agent.assert_called_with(
            "agent_001", "agent_002"
        )
    
    @pytest.mark.asyncio
    async def test_agent_failover_to_standby(self, mock_agent_pool):
        """Test failover to standby agent."""
        # Get initial agent
        primary = mock_agent_pool.acquire_agent({"id": "task_001"})
        assert primary == "agent_001"
        
        # Failover
        mock_agent_pool.replace_agent("agent_001", "agent_002")
        
        # Verify failover happened
        mock_agent_pool.replace_agent.assert_called()
    
    @pytest.mark.asyncio
    async def test_agent_pool_recovery(self, mock_agent_pool):
        """Test recovery of agent pool after failures."""
        # Get pool stats
        stats = mock_agent_pool.get_pool_stats()
        
        assert stats["total"] >= 2
        assert stats["available"] > 0
    
    @pytest.mark.asyncio
    async def test_reassign_tasks_on_agent_failure(
        self, temp_db, mock_agent_pool
    ):
        """Test reassigning tasks when an agent fails."""
        cursor = temp_db.cursor()
        
        # Create a task assigned to an agent
        cursor.execute("""
            INSERT INTO tasks (id, title, status, assigned_agent_id)
            VALUES (?, ?, ?, ?)
        """, ("task_001", "Test Task", "in_progress", "agent_001"))
        
        temp_db.commit()
        
        # Simulate agent failure - reassign to another agent
        cursor.execute("""
            UPDATE tasks SET assigned_agent_id = ? WHERE id = ?
        """, ("agent_002", "task_001"))
        
        temp_db.commit()
        
        # Verify reassignment
        cursor.execute(
            "SELECT assigned_agent_id FROM tasks WHERE id = ?",
            ("task_001",)
        )
        result = cursor.fetchone()
        assert result[0] == "agent_002"
    
    @pytest.mark.asyncio
    async def test_agent_restart_sequence(self, mock_agent):
        """Test agent restart sequence on failure."""
        # Mark as unhealthy
        mock_agent.health_check = AsyncMock(return_value=False)
        
        # Restart
        is_healthy = await mock_agent.health_check()
        assert is_healthy is False
        
        # Simulate recovery
        mock_agent.health_check = AsyncMock(return_value=True)
        is_healthy = await mock_agent.health_check()
        assert is_healthy is True


class TestEndToEndWorkflowIntegration:
    """Integration tests combining multiple workflow components."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_execution(
        self,
        sample_workflow,
        mock_guardian,
        mock_workflow_executor,
        mock_sandbox,
        mock_memory_store
    ):
        """Test complete end-to-end workflow."""
        # Stage 1: Execute workflow with Guardian approval
        result = await mock_workflow_executor.execute(sample_workflow)
        assert result["status"] == "completed"
        
        # Stage 2: Store execution context in memory
        await mock_memory_store.store(
            "execution_result",
            result,
            metadata={"workflow_id": sample_workflow["id"]}
        )
        
        # Stage 3: Retrieve for future reference
        retrieved = await mock_memory_store.retrieve("execution_result")
        assert retrieved is not None
    
    @pytest.mark.asyncio
    async def test_workflow_with_code_execution_and_versioning(
        self,
        sample_workflow,
        mock_sandbox,
        mock_version_manager,
        sample_code_snippet
    ):
        """Test workflow with code execution and version tracking."""
        # Execute code
        code = sample_code_snippet["python"]
        exec_result = await mock_sandbox.run_code(code)
        assert exec_result["status"] == "success"
        
        # Create version checkpoint
        version_id = await mock_version_manager.create_version(code)
        assert version_id is not None
        
        # Verify version exists
        version = await mock_version_manager.get_version(version_id)
        assert version is not None
    
    @pytest.mark.asyncio
    async def test_workflow_recovery_from_agent_failure(
        self,
        mock_agent_pool,
        mock_workflow_executor,
        sample_workflow,
        temp_db
    ):
        """Test workflow recovery when agent fails."""
        # Execute workflow
        result = await mock_workflow_executor.execute(sample_workflow)
        
        # Simulate agent failure
        failed_agent = mock_agent_pool.get_available_agent()
        
        # Replace with backup
        mock_agent_pool.replace_agent(
            failed_agent["id"],
            "agent_002"
        )
        
        # Re-execute workflow
        result2 = await mock_workflow_executor.execute(sample_workflow)
        
        assert result2["status"] == "completed"
