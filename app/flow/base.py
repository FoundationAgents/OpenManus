from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
import uuid

from pydantic import BaseModel, Field

from app.agent.base import BaseAgent
from app.event.init import ensure_event_system_initialized
from app.logger import logger


class BaseFlow(BaseModel, ABC):
    """Base class for execution flows supporting multiple agents"""

    agents: Dict[str, BaseAgent]
    tools: Optional[List] = None
    primary_agent_key: Optional[str] = None

    # Event system integration
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID for event tracking")
    enable_events: bool = Field(default=True, description="Whether to publish flow events")
    flow_name: str = Field(default="BaseFlow", description="Name of the flow for event identification")

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        # Handle different ways of providing agents
        if isinstance(agents, BaseAgent):
            agents_dict = {"default": agents}
        elif isinstance(agents, list):
            agents_dict = {f"agent_{i}": agent for i, agent in enumerate(agents)}
        else:
            agents_dict = agents

        # If primary agent not specified, use first agent
        primary_key = data.get("primary_agent_key")
        if not primary_key and agents_dict:
            primary_key = next(iter(agents_dict))
            data["primary_agent_key"] = primary_key

        # Set the agents dictionary
        data["agents"] = agents_dict

        # Generate conversation ID if not provided
        if "conversation_id" not in data or data["conversation_id"] is None:
            data["conversation_id"] = str(uuid.uuid4())

        # Set flow name if not provided
        if "flow_name" not in data:
            data["flow_name"] = self.__class__.__name__

        # Initialize using BaseModel's init
        super().__init__(**data)

        # Initialize event system if events are enabled
        if self.enable_events:
            ensure_event_system_initialized()

        # Propagate conversation ID to agents
        self._propagate_conversation_id()

    @property
    def primary_agent(self) -> Optional[BaseAgent]:
        """Get the primary agent for the flow"""
        return self.agents.get(self.primary_agent_key)

    def get_agent(self, key: str) -> Optional[BaseAgent]:
        """Get a specific agent by key"""
        return self.agents.get(key)

    def add_agent(self, key: str, agent: BaseAgent) -> None:
        """Add a new agent to the flow"""
        self.agents[key] = agent
        # Propagate conversation ID to new agent
        if hasattr(agent, 'set_conversation_id') and self.conversation_id:
            agent.set_conversation_id(self.conversation_id)

    @abstractmethod
    async def execute(self, input_text: str) -> str:
        """Execute the flow with given input"""
        pass

    # Event system integration methods

    def _propagate_conversation_id(self) -> None:
        """Propagate conversation ID to all agents."""
        if self.conversation_id:
            for agent in self.agents.values():
                if hasattr(agent, 'set_conversation_id'):
                    agent.set_conversation_id(self.conversation_id)

    def set_conversation_id(self, conversation_id: str) -> None:
        """Set the conversation ID for the flow and all agents."""
        self.conversation_id = conversation_id
        self._propagate_conversation_id()

    def enable_event_publishing(self, enabled: bool = True) -> None:
        """Enable or disable event publishing for the flow."""
        self.enable_events = enabled
        if enabled:
            ensure_event_system_initialized()

    async def publish_flow_start_event(self, input_text: str) -> bool:
        """Publish flow execution start event."""
        if not self.enable_events:
            return False

        try:
            from app.event import BaseEvent, publish_event

            event = BaseEvent(
                event_type="flow.execution.start",
                data={
                    "flow_name": self.flow_name,
                    "flow_type": self.__class__.__name__,
                    "conversation_id": self.conversation_id,
                    "input_text": input_text,
                    "agent_count": len(self.agents),
                    "primary_agent": self.primary_agent_key
                },
                source=self.flow_name
            )
            return await publish_event(event)
        except Exception as e:
            logger.warning(f"Failed to publish flow start event: {e}")
            return False

    async def publish_flow_complete_event(self, result: str, success: bool = True) -> bool:
        """Publish flow execution complete event."""
        if not self.enable_events:
            return False

        try:
            from app.event import BaseEvent, publish_event

            event = BaseEvent(
                event_type="flow.execution.complete",
                data={
                    "flow_name": self.flow_name,
                    "flow_type": self.__class__.__name__,
                    "conversation_id": self.conversation_id,
                    "result": result,
                    "success": success
                },
                source=self.flow_name
            )
            return await publish_event(event)
        except Exception as e:
            logger.warning(f"Failed to publish flow complete event: {e}")
            return False

    async def publish_custom_flow_event(self, event_type: str, data: dict) -> bool:
        """Publish a custom flow event.

        Args:
            event_type: Type of the event (e.g., "flow.custom.decision")
            data: Event data dictionary

        Returns:
            bool: True if event was published successfully
        """
        if not self.enable_events:
            return False

        try:
            from app.event import BaseEvent, publish_event

            event = BaseEvent(
                event_type=event_type,
                data={
                    "flow_name": self.flow_name,
                    "flow_type": self.__class__.__name__,
                    "conversation_id": self.conversation_id,
                    **data
                },
                source=self.flow_name
            )
            return await publish_event(event)
        except Exception as e:
            logger.warning(f"Failed to publish custom flow event {event_type}: {e}")
            return False
