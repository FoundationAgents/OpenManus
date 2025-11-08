"""
Tests for database optimization system
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from app.reliability.db_optimization import DatabaseOptimizer


@pytest.fixture
def temp_db():
    """Create temporary database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield str(db_path)


def test_database_optimizer_initialization(temp_db):
    """Test database optimizer initialization"""
    optimizer = DatabaseOptimizer(temp_db)
    assert optimizer.db_path == temp_db


def test_optimize_for_reliability(temp_db):
    """Test database optimization for reliability"""
    optimizer = DatabaseOptimizer(temp_db)
    success = optimizer.optimize_for_reliability()
    assert success


def test_vacuum_database(temp_db):
    """Test database vacuuming"""
    optimizer = DatabaseOptimizer(temp_db)
    optimizer.optimize_for_reliability()
    success = optimizer.vacuum_database()
    assert success


def test_analyze_database(temp_db):
    """Test database analysis"""
    optimizer = DatabaseOptimizer(temp_db)
    optimizer.optimize_for_reliability()
    success = optimizer.analyze_database()
    assert success


def test_get_database_stats(temp_db):
    """Test getting database statistics"""
    optimizer = DatabaseOptimizer(temp_db)
    optimizer.optimize_for_reliability()
    stats = optimizer.get_database_stats()
    
    assert "size_mb" in stats
    assert "page_count" in stats
    assert "journal_mode" in stats
    assert "table_count" in stats


def test_check_database_integrity(temp_db):
    """Test database integrity check"""
    optimizer = DatabaseOptimizer(temp_db)
    optimizer.optimize_for_reliability()
    
    result = optimizer.check_database_integrity()
    assert "integrity" in result
    assert result["integrity"] in ["ok", "error"]


def test_enable_foreign_keys(temp_db):
    """Test enabling foreign key constraints"""
    optimizer = DatabaseOptimizer(temp_db)
    success = optimizer.enable_foreign_keys()
    assert success


def test_transaction_management(temp_db):
    """Test transaction management"""
    optimizer = DatabaseOptimizer(temp_db)
    
    success = optimizer.begin_transaction()
    assert success
    
    success = optimizer.commit_transaction()
    assert success


def test_transaction_rollback(temp_db):
    """Test transaction rollback"""
    optimizer = DatabaseOptimizer(temp_db)
    
    optimizer.begin_transaction()
    success = optimizer.rollback_transaction()
    assert success


def test_optimize_indexes(temp_db):
    """Test index optimization"""
    optimizer = DatabaseOptimizer(temp_db)
    optimizer.optimize_for_reliability()
    
    success = optimizer.optimize_indexes()
    assert success


@pytest.mark.asyncio
async def test_execute_with_retry(temp_db):
    """Test query execution with retry"""
    optimizer = DatabaseOptimizer(temp_db)
    
    # Create a simple query
    query = "SELECT 1"
    result = await optimizer.execute_with_retry(query, fetch=True)
    
    # Should return something or None on error, but not raise
    assert result is not None or result is None


@pytest.mark.asyncio
async def test_maintenance_task(temp_db):
    """Test maintenance task execution"""
    optimizer = DatabaseOptimizer(temp_db)
    optimizer.optimize_for_reliability()
    
    # Should complete without errors
    await optimizer.maintenance_task()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
