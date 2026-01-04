from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

import torch
from sentence_transformers import SentenceTransformer, util

from app.llm import LLM
from app.logger import logger
from app.sandbox.client import SANDBOX_CLIENT
from app.schema import ROLE_TYPE, AgentState, Memory, Message


class BaseAgent(BaseModel, ABC):  # ABC：用于规范子类行为，例如step()方法，如果子类不实现就无法初始化
    """Abstract base class for managing agent state and execution.

    Provides foundational functionality for state transitions, memory management,
    and a step-based execution loop. Subclasses must implement the `step` method.
    """

    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    # Prompts
    system_prompt: Optional[str] = Field(
        None, description="System-level instruction prompt"
    )
    next_step_prompt: Optional[str] = Field(
        None, description="Prompt for determining next action"
    )

    # Dependencies
    llm: LLM = Field(default_factory=LLM, description="Language model instance")  # default_factory和default是有区别的
    memory: Memory = Field(default_factory=Memory, description="Agent's memory store")  # default写法使得所有BaseAgent实例
    state: AgentState = Field(  # 共享一样Memory实例; 而default_factory写法在每次实例化BaseAgent时都会调用一次Memory进行实例化
        default=AgentState.IDLE, description="Current agent state"  # default写法对于一些可变对象是危险的(dict、list、自定义类等)
    )

    # Execution control
    max_steps: int = Field(default=10, description="Maximum steps before termination")
    current_step: int = Field(default=0, description="Current step in execution")

    duplicate_threshold: int = 2
    duplicate_count: int = 1
    embedding_model: SentenceTransformer = Field(
        default_factory=lambda: SentenceTransformer("all-MiniLM-L6-v2")
    )
    # store the embedding of the pre AI msg, avoiding calculate it again:
    last_msg_emb: dict = Field(default=dict())

    class Config:  # Pydantic模型中的一个内部配置类，不同于python中的Config类
        arbitrary_types_allowed = True  # 除了标准类型（如int、str）和已注册的Pydantic模型，可以使用自定义类作为字段类型，如前面 llm: LLM=...
        extra = "allow"  # Allow extra fields for flexibility in subclasses（如果设置为forbid，传入了模型中未定义的字段时会抛出错误，
        # 而现在这些字段会被保留在 .model_extra 中）

    @model_validator(mode="after")  # 在模型初始化完成后执行额外逻辑。
    def initialize_agent(self) -> "BaseAgent":
        """Initialize agent with default settings if not provided."""
        if self.llm is None or not isinstance(self.llm, LLM):
            self.llm = LLM(config_name=self.name.lower())
        if not isinstance(self.memory, Memory):
            self.memory = Memory()
        return self

    @asynccontextmanager  # 装饰器，用于定义异步上下文管理器，可以用async with来使用它
    async def state_context(self, new_state: AgentState):
        """Context manager for safe agent state transitions.

        Args:
            new_state: The state to transition to during the context.

        Yields:
            None: Allows execution within the new state.

        Raises:
            ValueError: If the new_state is invalid.
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")

        previous_state = self.state
        self.state = new_state
        try:
            yield  # 上下文管理器的核心：
            # 把控制权暂时交给 async with 块中的代码（即下方的 async with self.state_context(AgentState.RUNNING) ）
            # 在代码块执行期间，agent的状态为 `new_state`
        except Exception as e:  # 如果async with块中的代码发生错误，则修改状态并抛出异常
            self.state = AgentState.ERROR  # Transition to ERROR on failure
            raise e
        finally:  # 无论最后是否发生异常，都将状态恢复成原来的状态
            self.state = previous_state  # Revert to previous state

    def update_memory(
        self,
        role: ROLE_TYPE,  # type: ignore
        content: str,
        base64_image: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Add a message to the agent's memory.

        Args:
            role: The role of the message sender (user, system, assistant, tool).
            content: The message content.
            base64_image: Optional base64 encoded image.
            **kwargs: Additional arguments (e.g., tool_call_id for tool messages).

        Raises:
            ValueError: If the role is unsupported.
        """
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }

        if role not in message_map:
            raise ValueError(f"Unsupported message role: {role}")

        # Create message with appropriate parameters based on role
        kwargs = {"base64_image": base64_image, **(kwargs if role == "tool" else {})}
        self.memory.add_message(message_map[role](content, **kwargs))

    async def run(self, request: Optional[str] = None) -> str:
        """Execute the agent's main loop asynchronously.

        Args:
            request: Optional initial user request to process.

        Returns:
            A string summarizing the execution results.

        Raises:
            RuntimeError: If the agent is not in IDLE state at start.
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        if request:
            self.update_memory("user", request)

        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while (
                self.current_step < self.max_steps and self.state != AgentState.FINISHED
            ):
                self.current_step += 1
                logger.info(f"Executing step {self.current_step}/{self.max_steps}")
                step_result = await self.step()

                # Check for stuck state
                # if self.is_stuck():
                #     self.handle_stuck_state()
                self.update_duplicate_count()
                if self.duplicate_count == 2:
                    self.handle_stuck_state()
                elif self.duplicate_count > 2:
                    self.state = AgentState.FINISHED

                results.append(f"Step {self.current_step}: {step_result}")

            self.state = AgentState.IDLE
            if self.current_step >= self.max_steps:
                self.current_step = 0
                results.append(f"Terminated: Reached max steps ({self.max_steps})")
        await SANDBOX_CLIENT.cleanup()
        return "\n".join(results) if results else "No steps executed"

    @abstractmethod  # 抽象方法，当前（父类）只定义接口，不提供逻辑，且要求子类必须实现
    async def step(self) -> str:
        """Execute a single step in the agent's workflow.

        Must be implemented by subclasses to define specific behavior.
        """

    def handle_stuck_state(self):
        """Handle stuck state by adding a prompt to change strategy"""
        stuck_prompt = "\
        Observed duplicate responses. Consider new strategies and avoid repeating ineffective paths already attempted."
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt}"
        logger.warning(f"Agent detected stuck state. Added prompt: {stuck_prompt}")

    def update_duplicate_count(self):
        """Update the duplicate count of the agent's memory."""
        if len(self.memory.messages) < 2:
            return

        last_message = self.memory.messages[-1]
        if not last_message.content:
            return

        pre_content = None
        if last_message.role not in self.last_msg_emb:
            for msg in reversed(self.memory.messages[:-1]):
                if msg.role == last_message.role:
                    pre_content = msg.content
                    break
            if not pre_content:
                return
            self.last_msg_emb[last_message.role] = self.embedding_model.encode(pre_content, convert_to_tensor=True)

        # calculate the semantic similarity of the last two AI message:
        latest_emb = self.embedding_model.encode(last_message.content, convert_to_tensor=True)
        similarity = util.cos_sim(self.last_msg_emb[last_message.role], latest_emb).item()
        if similarity > 0.8:
            self.duplicate_count += 1
        elif self.duplicate_count != 1:  # reset it if not detecting duplicate content
            self.duplicate_count = 1
        self.last_msg_emb[last_message.role] = latest_emb

    def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate content"""
        if len(self.memory.messages) < 2:
            return False

        last_message = self.memory.messages[-1]
        if not last_message.content:
            return False

        # Count identical content occurrences
        duplicate_count = sum(
            1
            for msg in reversed(self.memory.messages[:-1])
            if msg.role == "assistant" and msg.content == last_message.content
        )

        return duplicate_count >= self.duplicate_threshold

    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value
