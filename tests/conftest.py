"""
Comprehensive test fixtures and configuration for E2E testing.

Provides:
- Temporary SQLite databases
- FAISS index setup
- Mock external services (HTTP, WebSocket, DNS)
- Guardian approvals mock
- Network client fixtures
- Memory/RAG fixtures
- Sandbox environment fixtures
"""

import asyncio
import json
import pytest
import tempfile
import sqlite3
import threading
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
from contextlib import contextmanager

import aiofiles
import numpy as np


# ============================================================================
# Markers
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "smoke: mark test as smoke test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "qt: mark test as Qt UI test (requires PyQt6)"
    )
    config.addinivalue_line(
        "markers", "asyncio: mark test as async test"
    )


# ============================================================================
# Event Loop and Async Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
async def async_context():
    """Async context for test execution."""
    yield
    await asyncio.sleep(0.01)


# ============================================================================
# Temporary Database Fixtures
# ============================================================================

@pytest.fixture
def temp_db_path():
    """Create a temporary SQLite database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield db_path
        if db_path.exists():
            db_path.unlink()


@pytest.fixture
def temp_db(temp_db_path):
    """Create and initialize a temporary SQLite database."""
    conn = sqlite3.connect(str(temp_db_path))
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT,
            status TEXT DEFAULT 'idle',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            assigned_agent_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assigned_agent_id) REFERENCES agents(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS approvals (
            id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            action TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workflow_id) REFERENCES workflows(id)
        )
    """)
    conn.commit()
    
    yield conn
    
    conn.close()


@pytest.fixture
async def async_db(temp_db_path):
    """Create an async SQLite database connection."""
    try:
        import aiosqlite
    except ImportError:
        pytest.skip("aiosqlite not installed")
    
    db = await aiosqlite.connect(str(temp_db_path))
    yield db
    await db.close()


# ============================================================================
# FAISS Vector Store Fixtures
# ============================================================================

@pytest.fixture
def faiss_index_path():
    """Create a temporary FAISS index path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "faiss_index"
        index_path.mkdir(exist_ok=True)
        yield index_path


@pytest.fixture
def mock_faiss_store(faiss_index_path):
    """Create a mock FAISS vector store."""
    try:
        import faiss
    except ImportError:
        pytest.skip("faiss not installed")
    
    dimension = 768
    index = faiss.IndexFlatL2(dimension)
    
    vectors = np.random.randn(10, dimension).astype(np.float32)
    index.add(vectors)
    
    faiss.write_index(index, str(faiss_index_path / "index.faiss"))
    
    return {
        "index_path": faiss_index_path,
        "index": index,
        "dimension": dimension,
        "vectors": vectors
    }


# ============================================================================
# Mock External Service Fixtures
# ============================================================================

class MockHTTPHandler(BaseHTTPRequestHandler):
    """Mock HTTP request handler for testing."""
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode())
        elif self.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"data": "mock_data"}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        if self.path == "/api/validate":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"valid": True}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress log messages."""
        pass


@pytest.fixture
def mock_http_server():
    """Create a mock HTTP server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    
    server = HTTPServer(("127.0.0.1", port), MockHTTPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    
    yield f"http://127.0.0.1:{port}"
    
    server.shutdown()


# ============================================================================
# Guardian/Security Fixtures
# ============================================================================

@pytest.fixture
def mock_guardian():
    """Create a mock Guardian service."""
    guardian = AsyncMock()
    
    guardian.validate = AsyncMock(return_value={
        "approved": True,
        "reason": "Safe command",
        "risk_level": "low"
    })
    
    guardian.request_approval = AsyncMock(return_value={
        "status": "approved",
        "request_id": "req_123"
    })
    
    guardian.deny = AsyncMock(return_value={
        "status": "denied",
        "reason": "Security policy violation"
    })
    
    return guardian


@pytest.fixture
def approval_request_fixture():
    """Create a sample Guardian approval request."""
    return {
        "id": "req_123",
        "action": "execute_code",
        "context": {
            "code": "print('hello')",
            "language": "python"
        },
        "risk_level": "medium",
        "created_at": "2024-01-01T00:00:00Z"
    }


# ============================================================================
# Network Client Fixtures
# ============================================================================

@pytest.fixture
def mock_network_client():
    """Create a mock network client with caching."""
    client = AsyncMock()
    
    cache = {}
    
    async def cached_request(url, method="GET"):
        """Make a request with caching."""
        cache_key = f"{method}:{url}"
        if cache_key in cache:
            return cache[cache_key]
        
        result = {"status": 200, "data": {"url": url}}
        cache[cache_key] = result
        return result
    
    client.request = AsyncMock(side_effect=cached_request)
    client.cache = cache
    client.clear_cache = MagicMock(side_effect=lambda: cache.clear())
    
    return client


# ============================================================================
# Memory/RAG Fixtures
# ============================================================================

@pytest.fixture
async def mock_memory_store():
    """Create a mock memory/RAG store."""
    store = AsyncMock()
    
    memory_data = {}
    
    async def store_memory(key, value, metadata=None):
        """Store a memory."""
        memory_data[key] = {
            "value": value,
            "metadata": metadata or {},
            "created_at": "2024-01-01T00:00:00Z"
        }
        return key
    
    async def retrieve_memory(key):
        """Retrieve a memory."""
        return memory_data.get(key, None)
    
    async def search_memory(query, limit=5):
        """Search memory."""
        results = []
        for k, v in memory_data.items():
            if query.lower() in str(v).lower():
                results.append((k, v))
                if len(results) >= limit:
                    break
        return results
    
    store.store = AsyncMock(side_effect=store_memory)
    store.retrieve = AsyncMock(side_effect=retrieve_memory)
    store.search = AsyncMock(side_effect=search_memory)
    store.data = memory_data
    
    return store


# ============================================================================
# Sandbox Environment Fixtures
# ============================================================================

@pytest.fixture
def mock_sandbox():
    """Create a mock sandbox environment."""
    sandbox = AsyncMock()
    
    execution_results = {}
    
    async def run_code(code, language="python", timeout=30):
        """Run code in sandbox."""
        result_id = f"exec_{len(execution_results)}"
        result = {
            "id": result_id,
            "status": "success",
            "output": f"Execution of {language} code: {code[:50]}...",
            "exit_code": 0,
            "duration_ms": 100
        }
        execution_results[result_id] = result
        return result
    
    sandbox.run_code = AsyncMock(side_effect=run_code)
    sandbox.get_result = AsyncMock(
        side_effect=lambda exec_id: execution_results.get(exec_id)
    )
    sandbox.list_results = AsyncMock(
        side_effect=lambda: list(execution_results.values())
    )
    
    return sandbox


@pytest.fixture
def mock_sandbox_environment():
    """Create a mock sandbox environment with capability grants."""
    env = MagicMock()
    
    env.check_capability = MagicMock(return_value=True)
    env.grant_capability = MagicMock(return_value=True)
    env.revoke_capability = MagicMock(return_value=True)
    env.create_isolated_container = MagicMock(return_value="container_123")
    env.execute_in_container = MagicMock(return_value={
        "status": "success",
        "output": "Command executed"
    })
    env.cleanup_container = MagicMock(return_value=True)
    
    return env


# ============================================================================
# Workflow Fixtures
# ============================================================================

@pytest.fixture
def sample_workflow():
    """Create a sample workflow for testing."""
    return {
        "id": "wf_001",
        "name": "Test Workflow",
        "description": "A test workflow for E2E testing",
        "stages": [
            {
                "id": "stage_1",
                "name": "Initial Analysis",
                "tasks": [
                    {
                        "id": "task_1",
                        "action": "analyze_request",
                        "requires_approval": False
                    }
                ]
            },
            {
                "id": "stage_2",
                "name": "Code Execution",
                "tasks": [
                    {
                        "id": "task_2",
                        "action": "execute_code",
                        "requires_approval": True
                    }
                ]
            }
        ],
        "status": "pending"
    }


@pytest.fixture
def mock_workflow_executor():
    """Create a mock workflow executor."""
    executor = AsyncMock()
    
    async def execute(workflow):
        """Execute a workflow."""
        return {
            "workflow_id": workflow.get("id"),
            "status": "completed",
            "results": {
                "stage_1": {"status": "success"},
                "stage_2": {"status": "success"}
            }
        }
    
    executor.execute = AsyncMock(side_effect=execute)
    
    return executor


# ============================================================================
# Versioning Fixtures
# ============================================================================

@pytest.fixture
def mock_version_manager():
    """Create a mock version manager."""
    manager = AsyncMock()
    
    versions = {
        "v1": {"content": "Initial version", "timestamp": "2024-01-01"},
        "v2": {"content": "Updated version", "timestamp": "2024-01-02"}
    }
    
    async def get_version(version_id):
        """Get a version."""
        return versions.get(version_id)
    
    async def create_version(content):
        """Create a new version."""
        version_id = f"v{len(versions) + 1}"
        versions[version_id] = {
            "content": content,
            "timestamp": "2024-01-03"
        }
        return version_id
    
    async def rollback(version_id):
        """Rollback to a version."""
        if version_id in versions:
            return {
                "status": "success",
                "current_version": version_id,
                "content": versions[version_id]["content"]
            }
        return {"status": "error", "reason": "Version not found"}
    
    manager.get_version = AsyncMock(side_effect=get_version)
    manager.create_version = AsyncMock(side_effect=create_version)
    manager.rollback = AsyncMock(side_effect=rollback)
    manager.versions = versions
    
    return manager


# ============================================================================
# Backup/Restore Fixtures
# ============================================================================

@pytest.fixture
async def mock_backup_manager():
    """Create a mock backup manager."""
    manager = AsyncMock()
    
    backups = {}
    
    async def create_backup(name, data):
        """Create a backup."""
        backup_id = f"bak_{len(backups)}"
        backups[backup_id] = {
            "id": backup_id,
            "name": name,
            "data": data,
            "created_at": "2024-01-01T00:00:00Z"
        }
        return backup_id
    
    async def restore_backup(backup_id):
        """Restore from a backup."""
        if backup_id in backups:
            backup = backups[backup_id]
            return {
                "status": "success",
                "restored_data": backup["data"]
            }
        return {"status": "error", "reason": "Backup not found"}
    
    async def list_backups():
        """List all backups."""
        return list(backups.values())
    
    manager.create_backup = AsyncMock(side_effect=create_backup)
    manager.restore_backup = AsyncMock(side_effect=restore_backup)
    manager.list_backups = AsyncMock(side_effect=list_backups)
    manager.backups = backups
    
    return manager


# ============================================================================
# Agent Fixtures
# ============================================================================

@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    agent = AsyncMock()
    
    async def execute_task(task):
        """Execute a task."""
        return {
            "task_id": task.get("id"),
            "status": "completed",
            "result": f"Task {task.get('id')} executed"
        }
    
    agent.id = "agent_001"
    agent.role = "developer"
    agent.status = "ready"
    agent.execute_task = AsyncMock(side_effect=execute_task)
    agent.health_check = AsyncMock(return_value=True)
    
    return agent


@pytest.fixture
def mock_agent_pool():
    """Create a mock agent pool."""
    pool = MagicMock()
    
    agents = [
        {"id": "agent_001", "role": "developer", "status": "ready"},
        {"id": "agent_002", "role": "developer", "status": "ready"},
        {"id": "agent_003", "role": "tester", "status": "ready"}
    ]
    
    pool.agents = agents
    pool.get_available_agent = MagicMock(return_value=agents[0])
    pool.acquire_agent = MagicMock(return_value="agent_001")
    pool.release_agent = MagicMock(return_value=True)
    pool.replace_agent = MagicMock(return_value=True)
    pool.get_pool_stats = MagicMock(return_value={
        "total": 3,
        "available": 3,
        "busy": 0
    })
    
    return pool


# ============================================================================
# MCP Tool Fixtures
# ============================================================================

@pytest.fixture
def mock_mcp_tools():
    """Create mock MCP tools."""
    tools = {
        "file_read": AsyncMock(return_value={"content": "File content"}),
        "file_write": AsyncMock(return_value={"status": "success"}),
        "execute_command": AsyncMock(return_value={"output": "Command output"}),
        "search": AsyncMock(return_value={"results": []}),
        "list_directory": AsyncMock(return_value={"files": []})
    }
    
    return tools


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def test_config():
    """Create a test configuration."""
    return {
        "llm": {
            "default_model": "gpt-4",
            "temperature": 0.7
        },
        "guardian": {
            "enabled": True,
            "approval_required": True
        },
        "sandbox": {
            "enabled": True,
            "timeout": 30
        },
        "memory": {
            "max_size": 1000,
            "persistence": True
        },
        "backup": {
            "enabled": True,
            "frequency": "hourly"
        }
    }


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    
    return logger


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / "source").mkdir()
        (workspace / "output").mkdir()
        (workspace / "cache").mkdir()
        
        yield workspace


@pytest.fixture
def sample_code_snippet():
    """Provide a sample code snippet for testing."""
    return {
        "python": """
def greet(name):
    return f"Hello, {name}!"

print(greet("World"))
""",
        "javascript": """
function greet(name) {
    return `Hello, ${name}!`;
}

console.log(greet("World"));
""",
        "bash": """
#!/bin/bash
echo "Hello, World!"
"""
    }
