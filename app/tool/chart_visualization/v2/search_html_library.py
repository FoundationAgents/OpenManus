from app.tool.base import BaseTool, ToolResult
from typing import ClassVar, Dict
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pathlib import Path
from app.config import config
from app.tool.file_operators import (
    FileOperator,
    LocalFileOperator,
    PathLike,
    SandboxFileOperator,
)
from typing import List

class SearchHtmlLibraryResponse(ToolResult):
    """Structured response from the SearchHtmlLibrary tool, inheriting ToolResult."""

    report_bootstrap_theme: str = Field(description="The theme of the bootstrap report")
    components_content: Dict[str, str] = Field(description="The UI components content as a dictionary (component_name: html_content)")

    def __str__(self) -> str:
        """Formatted string with indented HTML content"""
        components_info = []
        for name, content in self.components_content.items():
            components_info.append(
                f"【{name}】\n"
                f"{content.strip()}\n"
                f"{'-'*40}"
            )

        return (
            f"📊 Report Theme: {self.report_bootstrap_theme}\n\n"
            f"🛠️ Components Content:\n\n"
            f"{'\n'.join(components_info)}"
        )

class SearchHtmlLibrary(BaseTool):
    """A tool for searching the html library in users' local file system"""

    name: str = "search_html_library"
    description: str = """Check the type of user's input data, and select proper bootstrap theme and component from user's local file system.
    When user requires a report, you need to use this tool first, to search the corresponding ui components and serve as a reference for subsequent report generation.
    Then, use other tools to generate fancy report template, specific chart...
    Outputs: 1) HTML components, 2) Bootstrap theme """

    parameters: dict = {
        "type": "object",
        "properties": {
            "report_bootstrap_theme":{
                "description": "The theme of bootstrap template to use.",
                "enum": [
                    # Light themes
                    "Brite"
                    "Cerulean",
                    "Materia",
                    "Cosmo",
                    "Flatly",
                    "Journal",
                    "Litera",
                    "Lumen",
                    "Minty",
                    "Pulse",
                    "Sandstone",
                    "Simplex",
                    "Sketchy",
                    "Spacelab",
                    "United",
                    "Zephyr",

                    # Dark themes
                    "Cyborg",
                    "Darkly",
                    "Slate",
                    "Solar",
                    "Superhero",
                    "Vapor",
                    "Lux",

                    # Special styles
                    "Quartz",
                    "Morph",
                    "Yeti"
                ],
                "default": "Materia",
                "type": "string",
            },
            "components": {
                "description": "List of components to you will use in the report, you need to decide based on user's input data.",
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["blockquote", "card", "chart", "indicator", "list", "nav", "nvabar", "progress", "table", "typography"]
                },
                "default": ["card", "chart", "table"],
                "minItems": 2,
                "uniqueItems": True
            }
        },
        "required": ["report_bootstrap_theme", "components"],
    }

    _local_operator: LocalFileOperator = LocalFileOperator()
    _sandbox_operator: SandboxFileOperator = SandboxFileOperator()

    # def _get_operator(self, use_sandbox: bool) -> FileOperator:
    def _get_operator(self) -> FileOperator:
        """Get the appropriate file operator based on execution mode."""
        return (
            self._sandbox_operator
            if config.sandbox.use_sandbox
            else self._local_operator
        )

    async def execute(
        self,
        report_bootstrap_theme: str,
        components: List[str]
    ) -> SearchHtmlLibraryResponse:
        """
        Execute the tool with the given parameters.
        Reads HTML component files and returns their content in a dictionary.
        """
        operator = self._get_operator()
        components_content = {}  # Initialize an empty dictionary to store component contents

        for component in components:
            path = f"/home/vm3/JoyZhao/OSPP/OpenManus/workspace/html_library/{component}.html"
            print(f"Reading component: {path}")

            try:
                # Read the HTML file content
                component_content = await operator.read_file(path)
                # Store in dictionary with component name as key
                components_content[component] = component_content
            except Exception as e:
                print(f"Failed to read component {component}: {str(e)}")
                components_content[component] = f"Error loading {component} component"

        theme=f"https://cdn.jsdelivr.net/npm/bootswatch@5/dist/{report_bootstrap_theme.lower()}/bootstrap.min.css"
        return SearchHtmlLibraryResponse(
            report_bootstrap_theme=theme,
            components_content=components_content
        )
