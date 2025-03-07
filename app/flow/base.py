from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel

from app.agent.base import BaseAgent


class FlowType(str, Enum):
    """流程类型枚举，定义系统支持的不同流程类型"""
    PLANNING = "planning"  # 规划类型流程


class BaseFlow(BaseModel, ABC):
    """流程基类，支持多代理执行
    
    提供多代理管理和执行的基础功能架构。子类必须实现execute方法定义具体流程。
    """

    agents: Dict[str, BaseAgent]  # 代理字典，键为代理名称
    tools: Optional[List] = None  # 可用工具列表
    primary_agent_key: Optional[str] = None  # 主代理的键名

    class Config:
        arbitrary_types_allowed = True  # 允许任意类型

    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        """初始化流程对象
        
        Args:
            agents: 代理对象，可以是单个代理、代理列表或代理字典
            **data: 其他配置参数
        """
        # 处理不同方式提供的代理
        if isinstance(agents, BaseAgent):
            agents_dict = {"default": agents}
        elif isinstance(agents, list):
            agents_dict = {f"agent_{i}": agent for i, agent in enumerate(agents)}
        else:
            agents_dict = agents

        # 如果未指定主代理，使用第一个代理
        primary_key = data.get("primary_agent_key")
        if not primary_key and agents_dict:
            primary_key = next(iter(agents_dict))
            data["primary_agent_key"] = primary_key

        # 设置代理字典
        data["agents"] = agents_dict

        # 使用BaseModel的init初始化
        super().__init__(**data)

    @property
    def primary_agent(self) -> Optional[BaseAgent]:
        """获取流程的主代理
        
        Returns:
            主代理对象，如果不存在则返回None
        """
        return self.agents.get(self.primary_agent_key)

    def get_agent(self, key: str) -> Optional[BaseAgent]:
        """根据键获取特定代理
        
        Args:
            key: 代理键名
            
        Returns:
            指定的代理对象，如果不存在则返回None
        """
        return self.agents.get(key)

    def add_agent(self, key: str, agent: BaseAgent) -> None:
        """向流程添加新代理
        
        Args:
            key: 代理的键名
            agent: 要添加的代理对象
        """
        self.agents[key] = agent

    @abstractmethod
    async def execute(self, input_text: str) -> str:
        """执行流程处理输入文本
        
        Args:
            input_text: 要处理的输入文本
            
        Returns:
            处理结果字符串
        """
