from app.tool.base import BaseTool, ToolResult
from typing import ClassVar
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pathlib import Path
from app.config import config
from app.tool.chart_visualization.python_execute import NormalPythonExecute



class ReportTemplateGeneration(NormalPythonExecute):
    """A tool for generating the report template in users' local file system"""

    name: str = "report_template_generation"
    description: str = """Generate a customized HTML report template based on user input data and the natural language description of the report from the previous step.

    When user requires a report, you need to use the search_html_library tool first, and then use this tool based on your search result.
    In this tool, you will need to process two input parameters to generate a customized HTML report.
    (1) First Input Parameter: Analyze the user-provided dataset for the report and generate: A natural language suggestion for the HTML report customization (e.g., layout, structure, recommended charts, and visualizations).
    (2) Second Input Parameter: Based on the natural language suggestion, produce: Python code that dynamically generates the corresponding HTML report. The code should also save the HTML file to the local filesystem.
    Outputs:  HTML report template file path"""

    parameters: dict = {
        "type": "object",
        "properties": {
            "report_template_description": {
                "description": "Natural language suggestion for HTML report structure (layout, sections, chart recommendations). Focus on framework only - no actual content needed.",
                "type": "string",
            },
            "code": {
                "type": "string",
                "description": """Python code to generate an HTML template with standardized placeholders. Requirements:
1. **Use placeholder format: [placeholder: description]**
2. Generate template structure only - no real content or data
3. Use the components and theme you have searched before.
4. For text sections: Use placeholders for paragraphs/lists
5. For charts: Use iframe elements with placeholder paths (/workspace/visualization/[filename].html)
6. Maintain semantic HTML structure with appropriate classes

## Output Requirements
1. Generate **report_template.html** file
2. Print the file path: print(report_path)

Examples:
<div class="section">
    <h2>Executive Summary</h2>
    <div class="card">
        <p>[placeholder: 1-3 paragraph summary]</p>
        <div class="highlight">
            <strong>Key Findings:</strong>
            <ul>
                <li>[placeholder: Key insight 1]</li>
                <li>[placeholder: Key insight 2]</li>
            </ul>
        </div>
    </div>
</div>

<div class="section">
    <h2>[placeholder: Section name]</h2>
    <div class="card">
        <div class="card-header">[placeholder: Chart title]</div>
        <div class="card-body">
            <div class="chart-container">
                <iframe src="[placeholder: /workspace/visualization/chart_name.html]"
                    width="100%" height="100%" frameborder="0"></iframe>
            </div>
            <div class="mt-3">
                <h4>Key Insights:</h4>
                <ul>
                    <li>[placeholder: Chart insight 1]</li>
                    <li>[placeholder: Chart insight 2]</li>
                </ul>
            </div>
        </div>
    </div>
</div>"""
            },
        },
        "required": ["report_template_description", "code"],
    }
    async def execute(self, code: str, report_template_description: str | None = None, timeout=5):
        return await super().execute(code, timeout)
