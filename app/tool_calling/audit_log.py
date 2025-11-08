"""Audit logging for tool calling operations.

Provides:
- Comprehensive logging of all tool calls
- Searchable history
- Performance metrics
- Export functionality
"""

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.logger import logger


@dataclass
class ToolCallRecord:
    """Record of a tool call execution."""
    
    # Identity
    call_id: str
    tool_name: str
    timestamp: datetime
    
    # Execution details
    arguments: Dict[str, Any]
    result_success: bool
    result_output: Optional[str] = None
    result_error: Optional[str] = None
    
    # Performance
    execution_time: Optional[float] = None
    
    # Context
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    iteration: Optional[int] = None
    
    # Metadata
    cached: bool = False
    parallel_execution: bool = False
    guardian_validation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO format
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolCallRecord':
        """Create from dictionary."""
        # Convert ISO format to datetime
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class AuditLogger:
    """Logger for tool call audit trail."""
    
    def __init__(
        self,
        log_dir: Optional[Path] = None,
        max_memory_records: int = 1000,
        enable_file_logging: bool = True
    ):
        """Initialize audit logger.
        
        Args:
            log_dir: Directory for log files (default: workspace/logs/tool_calls)
            max_memory_records: Maximum records to keep in memory
            enable_file_logging: Whether to write logs to files
        """
        self.log_dir = log_dir
        self.max_memory_records = max_memory_records
        self.enable_file_logging = enable_file_logging
        
        # In-memory storage
        self._records: List[ToolCallRecord] = []
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_execution_time': 0.0,
            'cached_calls': 0
        }
        
        # Setup log directory
        if enable_file_logging and log_dir:
            self.log_dir = Path(log_dir)
            self.log_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Tool call audit logging enabled at: {self.log_dir}")
    
    def log_call(
        self,
        call_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        result_success: bool,
        result_output: Optional[str] = None,
        result_error: Optional[str] = None,
        execution_time: Optional[float] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        iteration: Optional[int] = None,
        cached: bool = False,
        parallel_execution: bool = False,
        guardian_validation: Optional[str] = None
    ) -> ToolCallRecord:
        """Log a tool call execution.
        
        Args:
            call_id: Unique call ID
            tool_name: Name of the tool
            arguments: Tool arguments
            result_success: Whether execution succeeded
            result_output: Output (if successful)
            result_error: Error message (if failed)
            execution_time: Execution time in seconds
            agent_id: Agent ID
            session_id: Session ID
            iteration: Iteration number
            cached: Whether result was cached
            parallel_execution: Whether executed in parallel
            guardian_validation: Guardian validation result
            
        Returns:
            ToolCallRecord
        """
        record = ToolCallRecord(
            call_id=call_id,
            tool_name=tool_name,
            timestamp=datetime.now(),
            arguments=arguments,
            result_success=result_success,
            result_output=result_output,
            result_error=result_error,
            execution_time=execution_time,
            agent_id=agent_id,
            session_id=session_id,
            iteration=iteration,
            cached=cached,
            parallel_execution=parallel_execution,
            guardian_validation=guardian_validation
        )
        
        with self._lock:
            # Add to memory
            self._records.append(record)
            
            # Trim if needed
            if len(self._records) > self.max_memory_records:
                self._records = self._records[-self.max_memory_records:]
            
            # Update statistics
            self._stats['total_calls'] += 1
            if result_success:
                self._stats['successful_calls'] += 1
            else:
                self._stats['failed_calls'] += 1
            if execution_time:
                self._stats['total_execution_time'] += execution_time
            if cached:
                self._stats['cached_calls'] += 1
        
        # Write to file
        if self.enable_file_logging and self.log_dir:
            self._write_to_file(record)
        
        logger.debug(f"Logged tool call: {tool_name} (success={result_success})")
        
        return record
    
    def _write_to_file(self, record: ToolCallRecord):
        """Write record to file.
        
        Args:
            record: Record to write
        """
        try:
            # Create daily log file
            date_str = record.timestamp.strftime('%Y-%m-%d')
            log_file = self.log_dir / f"tool_calls_{date_str}.jsonl"
            
            # Append record as JSON line
            with open(log_file, 'a') as f:
                f.write(json.dumps(record.to_dict()) + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def get_recent_calls(
        self,
        limit: int = 100,
        tool_name: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> List[ToolCallRecord]:
        """Get recent tool calls.
        
        Args:
            limit: Maximum number of records to return
            tool_name: Filter by tool name
            session_id: Filter by session ID
            
        Returns:
            List of records
        """
        with self._lock:
            records = self._records.copy()
        
        # Apply filters
        if tool_name:
            records = [r for r in records if r.tool_name == tool_name]
        if session_id:
            records = [r for r in records if r.session_id == session_id]
        
        # Return most recent
        return records[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get audit statistics.
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            stats = self._stats.copy()
            
            # Calculate derived stats
            if stats['total_calls'] > 0:
                stats['success_rate'] = stats['successful_calls'] / stats['total_calls']
                stats['average_execution_time'] = (
                    stats['total_execution_time'] / stats['total_calls']
                )
                stats['cache_hit_rate'] = stats['cached_calls'] / stats['total_calls']
            else:
                stats['success_rate'] = 0.0
                stats['average_execution_time'] = 0.0
                stats['cache_hit_rate'] = 0.0
            
            return stats
    
    def get_tool_usage(self) -> Dict[str, int]:
        """Get tool usage counts.
        
        Returns:
            Dictionary mapping tool names to call counts
        """
        usage = {}
        with self._lock:
            for record in self._records:
                usage[record.tool_name] = usage.get(record.tool_name, 0) + 1
        return usage
    
    def search_calls(
        self,
        tool_name: Optional[str] = None,
        success: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        contains_arg: Optional[str] = None
    ) -> List[ToolCallRecord]:
        """Search tool call records.
        
        Args:
            tool_name: Filter by tool name
            success: Filter by success status
            start_time: Filter by start time
            end_time: Filter by end time
            contains_arg: Filter by argument name
            
        Returns:
            Matching records
        """
        matches = []
        
        with self._lock:
            for record in self._records:
                # Apply filters
                if tool_name and record.tool_name != tool_name:
                    continue
                if success is not None and record.result_success != success:
                    continue
                if start_time and record.timestamp < start_time:
                    continue
                if end_time and record.timestamp > end_time:
                    continue
                if contains_arg and contains_arg not in record.arguments:
                    continue
                
                matches.append(record)
        
        return matches
    
    def export_to_json(self, filepath: Path) -> int:
        """Export all records to JSON file.
        
        Args:
            filepath: Output file path
            
        Returns:
            Number of records exported
        """
        with self._lock:
            records = [r.to_dict() for r in self._records]
        
        with open(filepath, 'w') as f:
            json.dump(records, f, indent=2)
        
        logger.info(f"Exported {len(records)} tool call records to {filepath}")
        return len(records)
    
    def clear(self):
        """Clear all in-memory records."""
        with self._lock:
            self._records.clear()
            logger.info("Cleared audit log records")


# Global instance
_global_audit_logger: Optional[AuditLogger] = None
_logger_lock = threading.RLock()


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance.
    
    Returns:
        Global AuditLogger
    """
    global _global_audit_logger
    
    with _logger_lock:
        if _global_audit_logger is None:
            from app.config import config, PROJECT_ROOT
            
            log_dir = PROJECT_ROOT / "workspace" / "logs" / "tool_calls"
            _global_audit_logger = AuditLogger(log_dir=log_dir)
        
        return _global_audit_logger


def set_audit_logger(logger: AuditLogger):
    """Set the global audit logger instance.
    
    Args:
        logger: AuditLogger instance
    """
    global _global_audit_logger
    with _logger_lock:
        _global_audit_logger = logger
