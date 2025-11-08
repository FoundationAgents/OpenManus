"""Adaptive Sandbox implementation with dynamic capability-based execution.

Main class that orchestrates dynamic sandbox creation based on granted capabilities,
Guardian validation, and intelligent isolation level management.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from app.logger import logger
from app.sandbox.adaptive.capability_grant import CapabilityGrant, GrantDecision
from app.sandbox.adaptive.isolation_levels import IsolationLevel
from app.sandbox.adaptive.builder import SandboxBuilder, SandboxEnvironment
from app.sandbox.adaptive.runtime_monitor import AdaptiveRuntimeMonitor, ResourceMetrics
from app.sandbox.core.guardian import Guardian, OperationRequest


@dataclass
class ExecutionContext:
    """Context for a sandbox execution."""
    
    execution_id: str
    agent_id: str
    grant_id: str
    command: str
    isolation_level: IsolationLevel
    environment: SandboxEnvironment
    started_at: float
    finished_at: Optional[float] = None
    status: str = "running"  # running, completed, failed, terminated
    output: str = ""
    error: Optional[str] = None
    exit_code: Optional[int] = None
    duration_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "agent_id": self.agent_id,
            "grant_id": self.grant_id,
            "command": self.command,
            "isolation_level": self.isolation_level.name,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "output_length": len(self.output),
            "error": self.error,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
        }


class AdaptiveSandbox:
    """Adaptive sandbox that constructs execution environment dynamically.
    
    Implements the full capability-based sandbox model:
    1. Agent requests capabilities via CapabilityGrant
    2. Guardian validates and approves/denies capabilities
    3. SandboxBuilder assembles environment just-in-time
    4. AdaptiveRuntimeMonitor watches for anomalies
    5. Isolation level escalates on detected risks
    6. Full audit trail maintained
    """
    
    def __init__(
        self,
        agent_id: str,
        grant: CapabilityGrant,
        guardian: Optional[Guardian] = None,
        isolation_level: Optional[IsolationLevel] = None,
    ):
        """Initialize adaptive sandbox.
        
        Args:
            agent_id: Agent ID
            grant: Capability grant
            guardian: Guardian validation instance
            isolation_level: Override isolation level determination
        """
        self.sandbox_id = f"adaptive_{uuid.uuid4().hex[:8]}"
        self.agent_id = agent_id
        self.grant = grant
        self.guardian = guardian
        self.isolation_level = isolation_level or IsolationLevel.RESTRICTED
        
        # Builder and environment
        self.builder: Optional[SandboxBuilder] = None
        self.environment: Optional[SandboxEnvironment] = None
        
        # Monitor
        self.monitor: Optional[AdaptiveRuntimeMonitor] = None
        
        # Execution history
        self.executions: List[ExecutionContext] = []
        self.current_execution: Optional[ExecutionContext] = None
        
        # State
        self.is_active = False
        self.created_at = time.time()
        
        logger.info(
            f"Created adaptive sandbox {self.sandbox_id} "
            f"for agent {agent_id} at isolation level {self.isolation_level.name}"
        )
    
    async def initialize(self) -> bool:
        """Initialize and validate the sandbox environment.
        
        Returns:
            True if initialization successful
        """
        try:
            # Guardian checkpoint: validate grant before creation
            if self.guardian:
                logger.debug(f"Running Guardian checkpoint for sandbox {self.sandbox_id}")
                
                # Create validation request
                operation_request = OperationRequest(
                    agent_id=self.agent_id,
                    operation="adaptive_sandbox_create",
                    metadata={
                        "sandbox_id": self.sandbox_id,
                        "grant_id": self.grant.grant_id,
                        "isolation_level": self.isolation_level.name,
                        "capabilities": {
                            "tools": list(self.grant.allowed_tools),
                            "paths": list(self.grant.allowed_paths.keys()),
                            "network": self.grant.network_enabled,
                        }
                    }
                )
                
                decision = await self.guardian.validate_operation(operation_request)
                
                if not decision.approved:
                    logger.error(
                        f"Guardian denied sandbox creation: {decision.reason} "
                        f"(risk: {decision.risk_level.value})"
                    )
                    return False
                
                logger.info(f"Guardian approved sandbox: {decision.reason}")
            
            # Build environment
            self.builder = SandboxBuilder(
                agent_id=self.agent_id,
                grant=self.grant,
                isolation_level=self.isolation_level,
            )
            self.environment = self.builder.build()
            
            # Initialize monitor
            self.monitor = AdaptiveRuntimeMonitor(
                sandbox_id=self.sandbox_id,
                initial_isolation_level=self.isolation_level,
            )
            
            self.is_active = True
            logger.info(f"Initialized sandbox {self.sandbox_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize sandbox: {e}")
            return False
    
    async def run_command(self, command: str, timeout: Optional[int] = None) -> Tuple[str, int, Optional[str]]:
        """Execute a command in the adaptive sandbox.
        
        Args:
            command: Command to execute
            timeout: Optional timeout in seconds
        
        Returns:
            Tuple of (output, exit_code, error_message)
        """
        if not self.is_active or not self.environment:
            raise RuntimeError("Sandbox not initialized")
        
        execution_id = str(uuid.uuid4())[:8]
        
        try:
            # Create execution context
            execution = ExecutionContext(
                execution_id=execution_id,
                agent_id=self.agent_id,
                grant_id=self.grant.grant_id,
                command=command,
                isolation_level=self.isolation_level,
                environment=self.environment,
                started_at=time.time(),
            )
            self.current_execution = execution
            self.executions.append(execution)
            
            logger.info(
                f"Executing command in sandbox {self.sandbox_id} "
                f"(execution={execution_id}): {command}"
            )
            
            # Guardian validation for command
            if self.guardian:
                operation_request = OperationRequest(
                    agent_id=self.agent_id,
                    operation="adaptive_command_execute",
                    command=command,
                    metadata={
                        "sandbox_id": self.sandbox_id,
                        "execution_id": execution_id,
                        "isolation_level": self.isolation_level.name,
                    }
                )
                
                decision = await self.guardian.validate_operation(operation_request)
                
                if not decision.approved:
                    error_msg = f"Guardian denied command execution: {decision.reason}"
                    logger.error(error_msg)
                    execution.status = "denied"
                    execution.error = error_msg
                    execution.finished_at = time.time()
                    execution.duration_seconds = execution.finished_at - execution.started_at
                    return "", -1, error_msg
            
            # Simulate command execution (real implementation would use subprocess/Docker)
            # This is a placeholder - real implementation depends on platform
            output, exit_code = await self._execute_command_impl(command, timeout)
            
            # Record execution success
            execution.status = "completed"
            execution.output = output
            execution.exit_code = exit_code
            execution.finished_at = time.time()
            execution.duration_seconds = execution.finished_at - execution.started_at
            
            logger.info(
                f"Command execution completed (execution={execution_id}): "
                f"exit_code={exit_code}, output_length={len(output)}"
            )
            
            return output, exit_code, None
            
        except asyncio.TimeoutError:
            error_msg = f"Command execution timed out after {timeout} seconds"
            logger.warning(f"Sandbox {self.sandbox_id}: {error_msg}")
            self.current_execution.status = "timeout"
            self.current_execution.error = error_msg
            self.current_execution.finished_at = time.time()
            self.current_execution.duration_seconds = self.current_execution.finished_at - self.current_execution.started_at
            return "", -1, error_msg
            
        except Exception as e:
            error_msg = f"Command execution failed: {str(e)}"
            logger.error(f"Sandbox {self.sandbox_id}: {error_msg}")
            
            if self.current_execution:
                self.current_execution.status = "failed"
                self.current_execution.error = error_msg
                self.current_execution.finished_at = time.time()
                self.current_execution.duration_seconds = self.current_execution.finished_at - self.current_execution.started_at
            
            return "", -1, error_msg
    
    async def _execute_command_impl(self, command: str, timeout: Optional[int]) -> Tuple[str, int]:
        """Platform-specific command execution implementation.
        
        This is a placeholder that should be overridden for real execution.
        """
        # Use timeout from grant if not specified
        if timeout is None:
            timeout = self.grant.timeout_seconds
        
        # Simulate execution with timeout
        try:
            # In real implementation, this would actually run the command
            # For now, return success
            await asyncio.sleep(0.1)
            return "Command executed successfully\n", 0
        except asyncio.TimeoutError:
            raise
    
    def get_environment_summary(self) -> Dict:
        """Get summary of the sandbox environment.
        
        Returns:
            Dictionary with environment configuration
        """
        if not self.environment:
            return {}
        
        return {
            "sandbox_id": self.sandbox_id,
            "agent_id": self.agent_id,
            "grant_id": self.grant.grant_id,
            "isolation_level": self.isolation_level.name,
            "created_at": self.created_at,
            "is_active": self.is_active,
            "environment": self.environment.to_dict(),
            "execution_count": len(self.executions),
        }
    
    def get_execution_history(self) -> List[Dict]:
        """Get history of command executions.
        
        Returns:
            List of execution contexts as dictionaries
        """
        return [e.to_dict() for e in self.executions]
    
    def get_monitoring_summary(self) -> Optional[Dict]:
        """Get runtime monitoring summary.
        
        Returns:
            Monitoring summary if available
        """
        if not self.monitor:
            return None
        return self.monitor.get_metrics_summary()
    
    async def cleanup(self) -> None:
        """Clean up sandbox resources."""
        logger.info(f"Cleaning up adaptive sandbox {self.sandbox_id}")
        
        if self.monitor:
            await self.monitor.stop_monitoring()
        
        self.is_active = False
    
    def suggest_environment_fix(self, error_message: str) -> List[str]:
        """Suggest missing capabilities to fix errors.
        
        Args:
            error_message: Error message from failed command
        
        Returns:
            List of suggestions
        """
        if not self.builder:
            return []
        
        suggestions = self.builder.suggest_required_capabilities(error_message)
        
        # Add isolation-specific suggestions
        if "Permission denied" in error_message and self.isolation_level.value > IsolationLevel.MONITORED.value:
            suggestions.append(
                f"Current isolation level is {self.isolation_level.name} - try lowering for more permissions"
            )
        
        return suggestions
