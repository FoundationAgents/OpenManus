from enum import Enum
from typing import Dict, List, Union, Optional

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow
from app.flow.planning import PlanningFlow


class FlowType(str, Enum):
    PLANNING = "planning"


class FlowFactory:
    """Factory for creating different types of flows with support for multiple agents and pool targeting"""

    @staticmethod
    def create_flow(
        flow_type: FlowType,
        agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]],
        target_pool: Optional[str] = None,
        **kwargs,
    ) -> BaseFlow:
        """
        Create a flow with optional pool targeting.
        
        Args:
            flow_type: Type of flow to create
            agents: Agent(s) for the flow
            target_pool: Optional target pool ID (e.g., 'main', 'gamedev', 'network')
            **kwargs: Additional arguments for the flow
            
        Returns:
            BaseFlow: Created flow instance
        """
        flows = {
            FlowType.PLANNING: PlanningFlow,
        }

        flow_class = flows.get(flow_type)
        if not flow_class:
            raise ValueError(f"Unknown flow type: {flow_type}")

        # Add pool targeting if specified
        if target_pool:
            kwargs['target_pool'] = target_pool
        
        return flow_class(agents, **kwargs)
