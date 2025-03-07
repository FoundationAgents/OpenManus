import json
import time
from typing import Dict, List, Optional, Union

from pydantic import Field

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow
from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Message
from app.tool import PlanningTool


class PlanningFlow(BaseFlow):
    """规划流程类，管理任务的规划和执行
    
    通过规划和执行两个阶段，协调多个代理完成复杂任务。
    """

    llm: LLM = Field(default_factory=lambda: LLM())  # 语言模型
    planning_tool: PlanningTool = Field(default_factory=PlanningTool)  # 规划工具
    executor_keys: List[str] = Field(default_factory=list)  # 执行者代理的键列表
    active_plan_id: str = Field(default_factory=lambda: f"plan_{int(time.time())}")  # 活动计划ID
    current_step_index: Optional[int] = None  # 当前执行的步骤索引

    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        """初始化规划流程
        
        Args:
            agents: 代理，可以是单个代理、代理列表或代理字典
            **data: 其他配置参数
        """
        # 在super().__init__之前设置executor_keys
        if "executors" in data:
            data["executor_keys"] = data.pop("executors")

        # 如果提供了计划ID则设置
        if "plan_id" in data:
            data["active_plan_id"] = data.pop("plan_id")

        # 如果未提供，则初始化规划工具
        if "planning_tool" not in data:
            planning_tool = PlanningTool()
            data["planning_tool"] = planning_tool

        # 使用处理后的数据调用父类的初始化方法
        super().__init__(agents, **data)

        # 如果未指定executor_keys，则使用所有代理键
        if not self.executor_keys:
            self.executor_keys = list(self.agents.keys())

    def get_executor(self, step_type: Optional[str] = None) -> BaseAgent:
        """获取当前步骤的适当执行代理
        
        根据步骤类型或需求选择代理。
        
        Args:
            step_type: 步骤类型，可选
            
        Returns:
            选择的执行代理
        """
        # 如果提供了步骤类型并且匹配代理键，则使用该代理
        if step_type and step_type in self.agents:
            return self.agents[step_type]

        # 否则使用第一个可用的执行者或回退到主代理
        for key in self.executor_keys:
            if key in self.agents:
                return self.agents[key]

        # 回退到主代理
        return self.primary_agent

    async def execute(self, input_text: str) -> str:
        """执行规划流程
        
        Args:
            input_text: 要处理的输入文本
            
        Returns:
            执行结果字符串
            
        Raises:
            ValueError: 如果没有主代理可用
        """
        try:
            if not self.primary_agent:
                raise ValueError("没有可用的主代理")

            # 如果提供了输入，则创建初始计划
            if input_text:
                await self._create_initial_plan(input_text)

                # 验证计划创建成功
                if self.active_plan_id not in self.planning_tool.plans:
                    logger.error(
                        f"计划创建失败。规划工具中找不到计划ID {self.active_plan_id}。"
                    )
                    return f"为以下内容创建计划失败: {input_text}"

            result = ""
            while True:
                # 获取要执行的当前步骤
                self.current_step_index, step_info = await self._get_current_step_info()

                # 如果没有更多步骤或计划完成则退出
                if self.current_step_index is None:
                    result += await self._finalize_plan()
                    break

                # 使用适当的代理执行当前步骤
                step_type = step_info.get("type") if step_info else None
                executor = self.get_executor(step_type)
                step_result = await self._execute_step(executor, step_info)
                result += step_result + "\n"

                # 检查代理是否想要终止
                if hasattr(executor, "state") and executor.state == AgentState.FINISHED:
                    break

            return result
        except Exception as e:
            logger.error(f"PlanningFlow错误: {str(e)}")
            return f"执行失败: {str(e)}"

    async def _create_initial_plan(self, request: str) -> None:
        """根据请求创建初始计划
        
        Args:
            request: 用户请求文本
        """
        logger.info(f"创建ID为 {self.active_plan_id} 的初始计划")

        # 为计划创建创建系统消息
        system_message = Message.system_message(
            "你是一个规划助手。你的任务是创建一个具有明确步骤的详细计划。"
        )

        # 使用请求创建用户消息
        user_message = Message.user_message(
            f"创建一个详细计划来完成这个任务: {request}"
        )

        # 使用PlanningTool调用LLM
        response = await self.llm.ask_tool(
            messages=[user_message],
            system_msgs=[system_message],
            tools=[self.planning_tool.to_param()],
            tool_choice="required",
        )

        # 如果存在工具调用则处理
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.function.name == "planning":
                    # 解析参数
                    args = tool_call.function.arguments
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            logger.error(f"解析工具参数失败: {args}")
                            continue

                    # 确保计划ID正确设置并执行工具
                    args["plan_id"] = self.active_plan_id

                    # 通过ToolCollection而不是直接执行工具
                    result = await self.planning_tool.execute(**args)

                    logger.info(f"计划创建结果: {str(result)}")
                    return

        # 如果执行到这里，创建默认计划
        logger.warning("创建默认计划")

        # 使用ToolCollection创建默认计划
        await self.planning_tool.execute(
            **{
                "command": "create",
                "plan_id": self.active_plan_id,
                "title": f"计划: {request[:50]}{'...' if len(request) > 50 else ''}",
                "steps": ["分析请求", "执行任务", "验证结果"],
            }
        )

    async def _get_current_step_info(self) -> tuple[Optional[int], Optional[dict]]:
        """获取当前步骤信息
        
        解析当前计划以识别第一个未完成步骤的索引和信息。
        如果没有找到活动步骤，则返回(None, None)。
        
        Returns:
            包含步骤索引和步骤信息的元组
        """
        if (
            not self.active_plan_id
            or self.active_plan_id not in self.planning_tool.plans
        ):
            logger.error(f"找不到ID为 {self.active_plan_id} 的计划")
            return None, None

        try:
            # 从规划工具存储直接访问计划数据
            plan_data = self.planning_tool.plans[self.active_plan_id]
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])

            # 查找第一个未完成的步骤
            for i, step in enumerate(steps):
                if i >= len(step_statuses):
                    status = "not_started"
                else:
                    status = step_statuses[i]

                if status in ["not_started", "in_progress"]:
                    # 提取步骤类型/类别(如果可用)
                    step_info = {"text": step}

                    # 尝试从文本中提取步骤类型(例如[SEARCH]或[CODE])
                    import re

                    type_match = re.search(r"\[([A-Z_]+)\]", step)
                    if type_match:
                        step_info["type"] = type_match.group(1).lower()

                    # 将当前步骤标记为进行中
                    try:
                        await self.planning_tool.execute(
                            command="mark_step",
                            plan_id=self.active_plan_id,
                            step_index=i,
                            step_status="in_progress",
                        )
                    except Exception as e:
                        logger.warning(f"将步骤标记为in_progress时出错: {e}")
                        # 如果需要，直接更新步骤状态
                        if i < len(step_statuses):
                            step_statuses[i] = "in_progress"
                        else:
                            while len(step_statuses) < i:
                                step_statuses.append("not_started")
                            step_statuses.append("in_progress")

                        plan_data["step_statuses"] = step_statuses

                    return i, step_info

            return None, None  # 未找到活动步骤

        except Exception as e:
            logger.warning(f"查找当前步骤索引时出错: {e}")
            return None, None

    async def _execute_step(self, executor: BaseAgent, step_info: dict) -> str:
        """使用指定代理执行当前步骤
        
        Args:
            executor: 执行代理
            step_info: 步骤信息字典
            
        Returns:
            步骤执行结果
        """
        # 为代理准备当前计划状态的上下文
        plan_status = await self._get_plan_text()
        step_text = step_info.get("text", f"步骤 {self.current_step_index}")

        # 为代理创建执行当前步骤的提示
        step_prompt = f"""
        当前计划状态:
        {plan_status}

        你的当前任务:
        你现在正在处理步骤 {self.current_step_index}: "{step_text}"

        请使用适当的工具执行此步骤。完成后，提供你完成的内容的摘要。
        """

        # 使用agent.run()执行步骤
        try:
            step_result = await executor.run(step_prompt)

            # 成功执行后将步骤标记为已完成
            await self._mark_step_completed()

            return step_result
        except Exception as e:
            logger.error(f"执行步骤 {self.current_step_index} 时出错: {e}")
            return f"执行步骤 {self.current_step_index} 时出错: {str(e)}"

    async def _mark_step_completed(self) -> None:
        """将当前步骤标记为已完成"""
        if self.current_step_index is None:
            return

        try:
            # 将步骤标记为已完成
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=self.current_step_index,
                step_status="completed",
            )
            logger.info(
                f"在计划 {self.active_plan_id} 中将步骤 {self.current_step_index} 标记为已完成"
            )
        except Exception as e:
            logger.warning(f"更新计划状态失败: {e}")
            # 直接在规划工具存储中更新步骤状态
            if self.active_plan_id in self.planning_tool.plans:
                plan_data = self.planning_tool.plans[self.active_plan_id]
                step_statuses = plan_data.get("step_statuses", [])

                # 确保step_statuses列表足够长
                while len(step_statuses) <= self.current_step_index:
                    step_statuses.append("not_started")

                # 更新状态
                step_statuses[self.current_step_index] = "completed"
                plan_data["step_statuses"] = step_statuses

    async def _get_plan_text(self) -> str:
        """获取当前计划的格式化文本
        
        Returns:
            计划文本
        """
        try:
            result = await self.planning_tool.execute(
                command="get", plan_id=self.active_plan_id
            )
            return result.output if hasattr(result, "output") else str(result)
        except Exception as e:
            logger.error(f"获取计划时出错: {e}")
            return self._generate_plan_text_from_storage()

    def _generate_plan_text_from_storage(self) -> str:
        """如果规划工具失败，直接从存储生成计划文本
        
        Returns:
            计划文本
        """
        try:
            if self.active_plan_id not in self.planning_tool.plans:
                return f"错误: 找不到ID为 {self.active_plan_id} 的计划"

            plan_data = self.planning_tool.plans[self.active_plan_id]
            title = plan_data.get("title", "无标题计划")
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])
            step_notes = plan_data.get("step_notes", [])

            # 确保step_statuses和step_notes与步骤数量匹配
            while len(step_statuses) < len(steps):
                step_statuses.append("not_started")
            while len(step_notes) < len(steps):
                step_notes.append("")

            # 按状态计数步骤
            status_counts = {
                "completed": 0,
                "in_progress": 0,
                "blocked": 0,
                "not_started": 0,
            }

            for status in step_statuses:
                if status in status_counts:
                    status_counts[status] += 1

            completed = status_counts["completed"]
            total = len(steps)
            progress = (completed / total) * 100 if total > 0 else 0

            plan_text = f"计划: {title} (ID: {self.active_plan_id})\n"
            plan_text += "=" * len(plan_text) + "\n\n"

            plan_text += (
                f"进度: {completed}/{total} 步骤已完成 ({progress:.1f}%)\n"
            )
            plan_text += f"状态: {status_counts['completed']} 已完成, {status_counts['in_progress']} 进行中, "
            plan_text += f"{status_counts['blocked']} 阻塞, {status_counts['not_started']} 未开始\n\n"
            plan_text += "步骤:\n"

            for i, (step, status, notes) in enumerate(
                zip(steps, step_statuses, step_notes)
            ):
                if status == "completed":
                    status_mark = "[✓]"
                elif status == "in_progress":
                    status_mark = "[→]"
                elif status == "blocked":
                    status_mark = "[!]"
                else:  # not_started
                    status_mark = "[ ]"

                plan_text += f"{i}. {status_mark} {step}\n"
                if notes:
                    plan_text += f"   备注: {notes}\n"

            return plan_text
        except Exception as e:
            logger.error(f"从存储生成计划文本时出错: {e}")
            return f"错误: 无法检索ID为 {self.active_plan_id} 的计划"

    async def _finalize_plan(self) -> str:
        """完成计划并使用流程的LLM直接提供摘要
        
        Returns:
            计划完成摘要
        """
        plan_text = await self._get_plan_text()

        # 使用流程的LLM直接创建摘要
        try:
            system_message = Message.system_message(
                "你是一个规划助手。你的任务是总结已完成的计划。"
            )

            user_message = Message.user_message(
                f"计划已完成。以下是最终计划状态:\n\n{plan_text}\n\n请提供已完成内容的摘要和任何最终想法。"
            )

            response = await self.llm.ask(
                messages=[user_message], system_msgs=[system_message]
            )

            return f"计划已完成:\n\n{response}"
        except Exception as e:
            logger.error(f"使用LLM完成计划时出错: {e}")

            # 回退到使用代理进行摘要
            try:
                agent = self.primary_agent
                summary_prompt = f"""
                计划已完成。以下是最终计划状态:

                {plan_text}

                请提供已完成内容的摘要和任何最终想法。
                """
                summary = await agent.run(summary_prompt)
                return f"计划已完成:\n\n{summary}"
            except Exception as e2:
                logger.error(f"使用代理完成计划时出错: {e2}")
                return "计划已完成。生成摘要时出错。"
