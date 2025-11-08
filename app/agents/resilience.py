"""
Agent Resilience Layer

Provides monitoring, health checking, and automatic replacement
for agents in the multi-agent environment.
"""

import asyncio
import time
import threading
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import json

from pydantic import BaseModel, Field
from app.logger import logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.flow.multi_agent_environment import (
        AgentPool, 
        SpecializedAgent, 
        DevelopmentTask,
        AgentRole,
        BlackboardMessage,
        MessageType
    )


class HealthStatus(str, Enum):
    """Agent health status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"
    REPLACED = "replaced"


class ResilienceEventType(str, Enum):
    """Types of resilience events"""
    HEALTH_CHECK = "health_check"
    FAILURE_DETECTED = "failure_detected"
    AGENT_REPLACEMENT = "agent_replacement"
    CONTEXT_TRANSFER = "context_transfer"
    RECOVERY_SUCCESS = "recovery_success"
    RECOVERY_FAILED = "recovery_failed"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class AgentTelemetry:
    """Telemetry data for agent monitoring"""
    agent_id: str
    role: "AgentRole"  # Use string literal to avoid circular import
    heartbeat: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    command_count: int = 0
    success_count: int = 0
    error_count: int = 0
    consecutive_errors: int = 0
    average_latency: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    task_completion_rate: float = 1.0
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None
    
    def update_success(self, latency: float = 0.0):
        """Update telemetry after successful command"""
        self.last_activity = time.time()
        self.heartbeat = time.time()
        self.command_count += 1
        self.success_count += 1
        self.consecutive_errors = 0
        
        if latency > 0:
            # Update average latency
            if self.command_count == 1:
                self.average_latency = latency
            else:
                self.average_latency = (self.average_latency * (self.command_count - 1) + latency) / self.command_count
    
    def update_error(self, error_msg: str):
        """Update telemetry after failed command"""
        self.last_activity = time.time()
        self.heartbeat = time.time()
        self.command_count += 1
        self.error_count += 1
        self.consecutive_errors += 1
        self.last_error = error_msg
        self.last_error_time = time.time()
    
    def get_health_score(self) -> float:
        """Calculate health score (0.0 to 1.0)"""
        if self.command_count == 0:
            return 1.0
        
        error_rate = self.error_count / self.command_count
        consecutive_penalty = min(self.consecutive_errors * 0.2, 0.8)
        
        # Penalize high latency (> 5 seconds)
        latency_penalty = max(0, (self.average_latency - 5.0) * 0.1)
        
        # Penalize inactivity (> 5 minutes)
        inactivity_penalty = max(0, (time.time() - self.last_activity) - 300) * 0.001
        
        health_score = max(0.0, 1.0 - error_rate - consecutive_penalty - latency_penalty - inactivity_penalty)
        return health_score
    
    def get_status(self) -> HealthStatus:
        """Determine health status based on telemetry"""
        health_score = self.get_health_score()
        
        if health_score >= 0.8:
            return HealthStatus.HEALTHY
        elif health_score >= 0.6:
            return HealthStatus.WARNING
        elif health_score >= 0.3:
            return HealthStatus.DEGRADED
        elif health_score > 0.0:
            return HealthStatus.FAILED
        else:
            return HealthStatus.FAILED


@dataclass
class ResilienceEvent:
    """Event in the resilience system"""
    id: str
    type: ResilienceEventType
    agent_id: str
    timestamp: float = field(default_factory=time.time)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"  # info, warning, error, critical


class ResilienceConfig(BaseModel):
    """Configuration for agent resilience"""
    
    # Health monitoring settings
    health_check_interval: float = Field(30.0, description="Health check interval in seconds")
    heartbeat_timeout: float = Field(120.0, description="Heartbeat timeout in seconds")
    inactivity_threshold: float = Field(300.0, description="Inactivity threshold in seconds")
    
    # Failure detection thresholds
    max_consecutive_errors: int = Field(3, description="Maximum consecutive errors before replacement")
    max_error_rate: float = Field(0.3, description="Maximum error rate (0.0 to 1.0)")
    max_latency: float = Field(10.0, description="Maximum average latency in seconds")
    min_health_score: float = Field(0.3, description="Minimum health score before replacement")
    
    # Replacement settings
    enable_auto_replacement: bool = Field(True, description="Enable automatic agent replacement")
    replacement_delay: float = Field(5.0, description="Delay before replacement in seconds")
    max_replacements_per_hour: int = Field(5, description="Maximum replacements per hour per role")
    
    # Context transfer settings
    context_retention_tasks: int = Field(10, description="Number of recent tasks to retain")
    context_retention_messages: int = Field(50, description="Number of recent messages to retain")
    context_retention_time: float = Field(3600.0, description="Context retention time in seconds")
    
    # Recovery settings
    enable_recovery_attempts: bool = Field(True, description="Enable recovery attempts before replacement")
    max_recovery_attempts: int = Field(2, description="Maximum recovery attempts")
    recovery_timeout: float = Field(60.0, description="Recovery attempt timeout")


class AgentFactory:
    """Factory for creating replacement agents"""
    
    def __init__(self, blackboard):
        self.blackboard = blackboard
        self.creation_count = 0
    
    def create_replacement_agent(self, original_agent: "SpecializedAgent", context: Dict[str, Any]) -> "SpecializedAgent":
        """Create a replacement agent with inherited context"""
        self.creation_count += 1
        agent_id = f"{original_agent.role.value}_replacement_{self.creation_count}"
        
        # Create new agent with same role
        replacement = self._create_agent_by_role(original_agent.role, agent_id)
        
        # Transfer context
        if context:
            self._transfer_context(replacement, context)
        
        logger.info(f"Created replacement agent {agent_id} for role {original_agent.role.value}")
        return replacement
    
    def _create_agent_by_role(self, role: "AgentRole", agent_id: str) -> "SpecializedAgent":
        """Create agent based on role"""
        from app.flow.specialized_agents import (
            ArchitectAgent, DeveloperAgent, TesterAgent, DevOpsAgent,
            SecurityAgent, ProductManagerAgent, UIUXDesignerAgent,
            DataAnalystAgent, DocumentationAgent, PerformanceAgent,
            CodeReviewerAgent, ResearcherAgent
        )
        
        agent_classes = {
            AgentRole.ARCHITECT: ArchitectAgent,
            AgentRole.DEVELOPER: DeveloperAgent,
            AgentRole.TESTER: TesterAgent,
            AgentRole.DEVOPS: DevOpsAgent,
            AgentRole.SECURITY: SecurityAgent,
            AgentRole.PRODUCT_MANAGER: ProductManagerAgent,
            AgentRole.UI_UX_DESIGNER: UIUXDesignerAgent,
            AgentRole.DATA_ANALYST: DataAnalystAgent,
            AgentRole.DOCUMENTATION: DocumentationAgent,
            AgentRole.PERFORMANCE: PerformanceAgent,
            AgentRole.CODE_REVIEWER: CodeReviewerAgent,
            AgentRole.RESEARCHER: ResearcherAgent
        }
        
        agent_class = agent_classes.get(role, SpecializedAgent)
        return agent_class(agent_id, self.blackboard, role=role)
    
    def _transfer_context(self, new_agent: "SpecializedAgent", context: Dict[str, Any]):
        """Transfer context to new agent"""
        # Transfer knowledge base
        if "knowledge_base" in context:
            new_agent.knowledge_base.update(context["knowledge_base"])
        
        # Transfer recent thoughts
        if "recent_thoughts" in context:
            new_agent.thoughts.extend(context["recent_thoughts"])
        
        # Transfer current task context
        if "current_task" in context:
            new_agent.current_task = context["current_task"]
        
        # Transfer collaboration partners
        if "collaboration_partners" in context:
            new_agent.collaboration_partners.update(context["collaboration_partners"])


class AgentHealthMonitor:
    """Monitor agent health and telemetry"""
    
    def __init__(self, config: ResilienceConfig):
        self.config = config
        self.telemetry: Dict[str, AgentTelemetry] = {}
        self.events: List[ResilienceEvent] = []
        self.callbacks: List[Callable[[ResilienceEvent], None]] = []
        self.lock = threading.Lock()
        self.running = False
        self.monitor_thread = None
        
        # Statistics
        self.replacement_counts: Dict[AgentRole, int] = {}
        self.replacement_times: List[float] = []
    
    def start_monitoring(self):
        """Start the health monitoring thread"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Agent health monitoring started")
    
    def stop_monitoring(self):
        """Stop the health monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        logger.info("Agent health monitoring stopped")
    
    def register_agent(self, agent_id: str, role: AgentRole):
        """Register an agent for monitoring"""
        with self.lock:
            self.telemetry[agent_id] = AgentTelemetry(agent_id=agent_id, role=role)
            logger.debug(f"Registered agent {agent_id} for health monitoring")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent from monitoring"""
        with self.lock:
            if agent_id in self.telemetry:
                del self.telemetry[agent_id]
                logger.debug(f"Unregistered agent {agent_id} from health monitoring")
    
    def update_agent_success(self, agent_id: str, latency: float = 0.0):
        """Update agent telemetry after successful operation"""
        with self.lock:
            if agent_id in self.telemetry:
                self.telemetry[agent_id].update_success(latency)
    
    def update_agent_error(self, agent_id: str, error_msg: str):
        """Update agent telemetry after failed operation"""
        with self.lock:
            if agent_id in self.telemetry:
                self.telemetry[agent_id].update_error(error_msg)
    
    def add_event_callback(self, callback: Callable[[ResilienceEvent], None]):
        """Add callback for resilience events"""
        self.callbacks.append(callback)
    
    def get_agent_telemetry(self, agent_id: str) -> Optional[AgentTelemetry]:
        """Get telemetry for specific agent"""
        with self.lock:
            return self.telemetry.get(agent_id)
    
    def get_all_telemetry(self) -> Dict[str, AgentTelemetry]:
        """Get telemetry for all agents"""
        with self.lock:
            return self.telemetry.copy()
    
    def get_recent_events(self, limit: int = 50) -> List[ResilienceEvent]:
        """Get recent resilience events"""
        with self.lock:
            return sorted(self.events, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""
        with self.lock:
            total_agents = len(self.telemetry)
            if total_agents == 0:
                return {"total_agents": 0, "healthy_agents": 0, "unhealthy_agents": 0}
            
            healthy_count = sum(1 for t in self.telemetry.values() 
                              if t.get_status() in [HealthStatus.HEALTHY, HealthStatus.WARNING])
            
            avg_health_score = sum(t.get_health_score() for t in self.telemetry.values()) / total_agents
            
            return {
                "total_agents": total_agents,
                "healthy_agents": healthy_count,
                "unhealthy_agents": total_agents - healthy_count,
                "average_health_score": avg_health_score,
                "recent_replacements": len([t for t in self.replacement_times 
                                          if time.time() - t < 3600]),
                "total_events": len(self.events)
            }
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._perform_health_checks()
                time.sleep(self.config.health_check_interval)
            except Exception as e:
                logger.error(f"Health monitoring loop error: {e}")
                time.sleep(5.0)
    
    def _perform_health_checks(self):
        """Perform health checks on all agents"""
        current_time = time.time()
        
        with self.lock:
            for agent_id, telemetry in self.telemetry.items():
                # Check for heartbeat timeout
                if current_time - telemetry.heartbeat > self.config.heartbeat_timeout:
                    self._create_event(
                        ResilienceEventType.FAILURE_DETECTED,
                        agent_id,
                        f"Heartbeat timeout: {current_time - telemetry.heartbeat:.1f}s",
                        {"timeout": current_time - telemetry.heartbeat},
                        "warning"
                    )
                
                # Check for consecutive errors
                if telemetry.consecutive_errors >= self.config.max_consecutive_errors:
                    self._create_event(
                        ResilienceEventType.FAILURE_DETECTED,
                        agent_id,
                        f"Consecutive errors threshold exceeded: {telemetry.consecutive_errors}",
                        {"consecutive_errors": telemetry.consecutive_errors},
                        "error"
                    )
                
                # Check health score
                health_score = telemetry.get_health_score()
                if health_score < self.config.min_health_score:
                    self._create_event(
                        ResilienceEventType.FAILURE_DETECTED,
                        agent_id,
                        f"Health score below threshold: {health_score:.2f}",
                        {"health_score": health_score},
                        "warning"
                    )
                
                # Regular health check event
                self._create_event(
                    ResilienceEventType.HEALTH_CHECK,
                    agent_id,
                    f"Health check - Score: {health_score:.2f}, Status: {telemetry.get_status().value}",
                    {
                        "health_score": health_score,
                        "status": telemetry.get_status().value,
                        "consecutive_errors": telemetry.consecutive_errors
                    }
                )
    
    def _create_event(self, event_type: ResilienceEventType, agent_id: str, 
                      description: str, metadata: Dict[str, Any] = None, 
                      severity: str = "info"):
        """Create and log a resilience event"""
        event = ResilienceEvent(
            id=f"{event_type.value}_{agent_id}_{int(time.time())}",
            type=event_type,
            agent_id=agent_id,
            description=description,
            metadata=metadata or {},
            severity=severity
        )
        
        self.events.append(event)
        
        # Keep only recent events (last 1000)
        if len(self.events) > 1000:
            self.events = self.events[-1000:]
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in resilience event callback: {e}")
        
        # Log event
        log_level = "info" if severity == "info" else "warning" if severity == "warning" else "error"
        getattr(logger, log_level)(f"Resilience Event: {description}")


class AgentResilienceManager:
    """Main resilience manager for agent replacement and recovery"""
    
    def __init__(self, agent_pools: "Dict[AgentRole, AgentPool]", blackboard, 
                 config: Optional[ResilienceConfig] = None):
        self.agent_pools = agent_pools
        self.blackboard = blackboard
        self.config = config or ResilienceConfig()
        self.health_monitor = AgentHealthMonitor(self.config)
        self.agent_factory = AgentFactory(blackboard)
        
        # Track agents and their contexts
        self.active_agents: "Dict[str, SpecializedAgent]" = {}
        self.agent_contexts: "Dict[str, Dict[str, Any]]" = {}
        
        # Replacement tracking
        self.replacement_history: List[Dict[str, Any]] = []
        self.replacement_lock = threading.Lock()
        
        # Setup event callback
        self.health_monitor.add_event_callback(self._handle_resilience_event)
        
        # Start monitoring
        self.health_monitor.start_monitoring()
        
        logger.info("Agent Resilience Manager initialized")
    
    def register_agent(self, agent: "SpecializedAgent"):
        """Register an agent for resilience management"""
        self.active_agents[agent.name] = agent
        self.health_monitor.register_agent(agent.name, agent.role)
        
        # Initialize context tracking
        self.agent_contexts[agent.name] = {
            "knowledge_base": {},
            "recent_thoughts": [],
            "current_task": None,
            "collaboration_partners": set(),
            "messages": []
        }
        
        logger.info(f"Registered agent {agent.name} for resilience management")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent from resilience management"""
        if agent_id in self.active_agents:
            del self.active_agents[agent_id]
        self.health_monitor.unregister_agent(agent_id)
        if agent_id in self.agent_contexts:
            del self.agent_contexts[agent_id]
        
        logger.info(f"Unregistered agent {agent_id} from resilience management")
    
    def update_agent_success(self, agent_id: str, latency: float = 0.0):
        """Update agent after successful operation"""
        self.health_monitor.update_agent_success(agent_id, latency)
        self._update_agent_context(agent_id)
    
    def update_agent_error(self, agent_id: str, error_msg: str):
        """Update agent after failed operation"""
        self.health_monitor.update_agent_error(agent_id, error_msg)
        self._update_agent_context(agent_id)
    
    def manually_replace_agent(self, agent_id: str, reason: str = "Manual intervention"):
        """Manually trigger agent replacement"""
        if agent_id not in self.active_agents:
            logger.warning(f"Agent {agent_id} not found for manual replacement")
            return False
        
        self.health_monitor._create_event(
            ResilienceEventType.MANUAL_INTERVENTION,
            agent_id,
            f"Manual replacement triggered: {reason}",
            {"reason": reason},
            "warning"
        )
        
        return self._replace_agent(agent_id, "manual")
    
    def get_resilience_status(self) -> Dict[str, Any]:
        """Get overall resilience status"""
        return {
            "health_summary": self.health_monitor.get_health_summary(),
            "active_agents": list(self.active_agents.keys()),
            "recent_events": self.health_monitor.get_recent_events(20),
            "replacement_history": self.replacement_history[-10:],
            "config": self.config.dict()
        }
    
    def shutdown(self):
        """Shutdown the resilience manager"""
        self.health_monitor.stop_monitoring()
        logger.info("Agent Resilience Manager shutdown")
    
    def _handle_resilience_event(self, event: ResilienceEvent):
        """Handle resilience events"""
        if event.type == ResilienceEventType.FAILURE_DETECTED:
            if self.config.enable_auto_replacement:
                # Check if we should replace the agent
                if self._should_replace_agent(event.agent_id):
                    logger.warning(f"Triggering replacement for agent {event.agent_id}")
                    self._replace_agent(event.agent_id, "auto")
    
    def _should_replace_agent(self, agent_id: str) -> bool:
        """Determine if agent should be replaced"""
        telemetry = self.health_monitor.get_agent_telemetry(agent_id)
        if not telemetry:
            return False
        
        # Check replacement rate limits
        recent_replacements = len([
            r for r in self.replacement_history
            if time.time() - r["timestamp"] < 3600 and r["role"] == telemetry.role
        ])
        
        if recent_replacements >= self.config.max_replacements_per_hour:
            logger.warning(f"Replacement rate limit exceeded for role {telemetry.role.value}")
            return False
        
        # Check various failure conditions
        if telemetry.consecutive_errors >= self.config.max_consecutive_errors:
            return True
        
        if telemetry.get_health_score() < self.config.min_health_score:
            return True
        
        # Check error rate
        if telemetry.command_count > 10:
            error_rate = telemetry.error_count / telemetry.command_count
            if error_rate > self.config.max_error_rate:
                return True
        
        return False
    
    def _replace_agent(self, agent_id: str, replacement_type: str):
        """Replace a failed agent"""
        with self.replacement_lock:
            try:
                if agent_id not in self.active_agents:
                    logger.warning(f"Agent {agent_id} not found for replacement")
                    return False
                
                original_agent = self.active_agents[agent_id]
                
                # Extract context
                context = self._extract_agent_context(agent_id)
                
                # Create replacement
                replacement_agent = self.agent_factory.create_replacement_agent(
                    original_agent, context
                )
                
                # Update agent pool
                pool = self.agent_pools.get(original_agent.role)
                if pool:
                    # Remove original agent from pool
                    if agent_id in pool.agents:
                        pool.agents.remove(agent_id)
                    if agent_id in pool.busy_agents:
                        pool.busy_agents.remove(agent_id)
                        if agent_id in pool.agent_tasks:
                            del pool.agent_tasks[agent_id]
                    
                    # Add replacement to pool
                    pool.add_agent(replacement_agent.name)
                
                # Update tracking
                self.unregister_agent(agent_id)
                self.register_agent(replacement_agent)
                
                # Log replacement
                replacement_record = {
                    "timestamp": time.time(),
                    "original_agent": agent_id,
                    "replacement_agent": replacement_agent.name,
                    "role": original_agent.role.value,
                    "type": replacement_type,
                    "context_size": len(str(context))
                }
                self.replacement_history.append(replacement_record)
                
                # Keep only recent history
                if len(self.replacement_history) > 100:
                    self.replacement_history = self.replacement_history[-100:]
                
                # Post replacement event to blackboard
                self.blackboard.post_message(BlackboardMessage(
                    id=f"agent_replacement_{int(time.time())}",
                    type=MessageType.INFO,
                    sender="resilience_manager",
                    recipient=None,
                    content=f"Agent {agent_id} replaced by {replacement_agent.name}",
                    metadata={
                        "type": "agent_replacement",
                        "original_agent": agent_id,
                        "replacement_agent": replacement_agent.name,
                        "role": original_agent.role.value
                    }
                ))
                
                # Create resilience event
                self.health_monitor._create_event(
                    ResilienceEventType.AGENT_REPLACEMENT,
                    agent_id,
                    f"Agent replaced by {replacement_agent.name}",
                    replacement_record,
                    "info"
                )
                
                logger.info(f"Successfully replaced agent {agent_id} with {replacement_agent.name}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to replace agent {agent_id}: {e}")
                self.health_monitor._create_event(
                    ResilienceEventType.RECOVERY_FAILED,
                    agent_id,
                    f"Replacement failed: {str(e)}",
                    {"error": str(e)},
                    "error"
                )
                return False
    
    def _extract_agent_context(self, agent_id: str) -> Dict[str, Any]:
        """Extract context from an agent"""
        agent = self.active_agents.get(agent_id)
        if not agent:
            return {}
        
        context = self.agent_contexts.get(agent_id, {}).copy()
        
        # Add current task context
        if agent.current_task:
            context["current_task"] = agent.current_task
        
        # Add recent thoughts (last 20)
        context["recent_thoughts"] = agent.thoughts[-20:]
        
        # Add knowledge base
        context["knowledge_base"] = agent.knowledge_base.copy()
        
        # Add collaboration partners
        context["collaboration_partners"] = agent.collaboration_partners.copy()
        
        # Get recent blackboard messages
        recent_time = time.time() - self.config.context_retention_time
        recent_messages = self.blackboard.get_messages(
            agent_id, 
            since=recent_time
        )
        context["messages"] = recent_messages[-self.config.context_retention_messages:]
        
        return context
    
    def _update_agent_context(self, agent_id: str):
        """Update context tracking for an agent"""
        if agent_id not in self.agent_contexts:
            return
        
        agent = self.active_agents.get(agent_id)
        if not agent:
            return
        
        context = self.agent_contexts[agent_id]
        
        # Update knowledge base periodically
        if hasattr(agent, 'knowledge_base'):
            context["knowledge_base"] = agent.knowledge_base.copy()
        
        # Update current task
        if hasattr(agent, 'current_task'):
            context["current_task"] = agent.current_task
        
        # Update collaboration partners
        if hasattr(agent, 'collaboration_partners'):
            context["collaboration_partners"] = agent.collaboration_partners.copy()
