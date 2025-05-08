from app.tool.base import BaseTool
from app.llm import LLM
from pydantic import Field
from app.prompt.validator import TEXT_VALIDATION_PROMPT, USER_CONTENT


_VALIDATE_DESCRIPTION = """
This tool evaluates the quality and completeness of a subtask result against a set of predefined criteria.
It checks whether the result fully satisfies task requirements, maintains high quality in terms of clarity, accuracy, and formatting,
 and determines whether improvements have been made in comparison to prior versions.
 If the result is satisfactory or improvements are minimal, it returns "The step result has already reached the requirement.".
 Otherwise, it provides detailed feedback and a revised version of the result that meets all requirements and is ready for downstream use.
"""


class Validator(BaseTool):
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    name: str = "validator"
    description: str = _VALIDATE_DESCRIPTION
    parameters: dict = {}

    async def validate(self, request: str, history: str):
        """Abstract method for result validate logic.

        Args:
            step_result: The result string to validate.
        """
        system_content = TEXT_VALIDATION_PROMPT
        user_content = USER_CONTENT.format(
            request=request, history=history
        )

        feedback = await self.llm.ask(
            messages=[{"role": "user", "content": user_content}],
            system_msgs=[{"role": "system", "content": system_content}],
        )
        return feedback

    async def execute(self, request: str, history: str) -> str:
        """Finish the current execution"""
        return await self.validate(request, history)
