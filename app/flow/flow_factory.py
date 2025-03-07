from typing import Dict, List, Union

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow, FlowType
from app.flow.planning import PlanningFlow


class FlowFactory:
    """流程工厂类，用于创建不同类型的流程
    
    实现工厂模式，根据流程类型创建相应的流程实例。
    """

    @staticmethod
    def create_flow(
        flow_type: FlowType,
        agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]],
        **kwargs,
    ) -> BaseFlow:
        """创建指定类型的流程实例
        
        Args:
            flow_type: 流程类型，来自FlowType枚举
            agents: 代理，可以是单个代理、代理列表或代理字典
            **kwargs: 传递给流程构造函数的其他参数
            
        Returns:
            创建的流程实例
            
        Raises:
            ValueError: 如果指定了未知的流程类型
        """
        flows = {
            FlowType.PLANNING: PlanningFlow,
        }

        flow_class = flows.get(flow_type)
        if not flow_class:
            raise ValueError(f"未知的流程类型: {flow_type}")

        return flow_class(agents, **kwargs)
