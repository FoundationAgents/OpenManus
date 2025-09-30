from app.tool.chart_visualization.python_execute import NormalPythonExecute
from typing import ClassVar
from pathlib import Path

class GenerateInitialReport(NormalPythonExecute):
    """A tool for generating initial data analysis reports based on the report template and user's input data"""

    name: str = "generate_initial_report"
    description: str = """Generates an initial HTML data analysis report based on the report template and user's input data.
    After searhing and reading the report template, you should dynamically adapt the template content according to user input data,
    intelligently determine which charts should be included in the report,
    and automatically populate the fillable placeholders with corresponding data.

    Outputs: 1) HTML report file path"""

    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": f"""Python code for generating initial HTML data report based on the report template and user's input data.

## Output Requirements
1. Generate initial_report.html file
2. Print the file path: print(report_path)

# Notes:
1. Refer to the searched report templates
2. Complete the applicable placeholders, and leave any unfilled ones as '[placeholder: ...]'.

""",
            },
        },
        "required": ["code", "code_type"],
    }
