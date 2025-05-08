from app.tool.base import BaseTool
from app.llm import LLM
from pydantic import Field
from app.prompt.latex_generator import SYSTEM_PROMPT, USER_CONTENT


_Latex_Generator_DESCRIPTION = """
This agent generates complete, high-quality LaTeX documents with a focus on Beamer presentations. It accepts topic-specific input and produces fully self-contained LaTeX source code, including all required packages, structures, and rich content elements such as equations, figures, and formatted text. The agent ensures completeness by avoiding any placeholders or incomplete sections.

In addition to generation, the agent supports iterative refinement: it evaluates and improves the generated LaTeX code based on validation feedback to ensure correctness, formatting quality, and logical structure. The final output is ready for immediate compilation and professional presentation use.
"""

class LatexGenerator(BaseTool):
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    name: str = "latexgenerator"
    description: str = _Latex_Generator_DESCRIPTION
    parameters: dict = {}

    async def generate(self, request: str, history: str=""):
        """Abstract method for result validate logic.

        Args:
            step_result: The result string to validate.
        """
        system_content = SYSTEM_PROMPT
        user_content = USER_CONTENT.format(
            request=request, history=history
        )

        feedback = await self.llm.ask(
            messages=[{"role": "user", "content": user_content}],
            system_msgs=[{"role": "system", "content": system_content}],
        )
        return feedback

    async def execute(self, request: str, history: str="") -> str:
        """Finish the current execution"""
        return await self.generate(request, history)
