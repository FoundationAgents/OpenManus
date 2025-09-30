from app.tool.chart_visualization.python_execute import NormalPythonExecute

class GenerateFinalReport(NormalPythonExecute):
    """A tool for generating final data analysis report"""

    name: str = "generate_final_report"
    description: str = """Replace the all placeholders in initial report and refine to generate final report.
    Outputs: 1) HTML report file path"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "code_type": {
                "description": "code type, replacing: html with placeholders -> html with specific chart; check_refine: Make final adjustments and checks on the report",
                "type": "string",
                "default": "replacing",
                "enum": ["replacing", "check_refine"],
            },
            "code": {
                "type": "string",
                "description": """Python code for replacing chart placeholders with specific chart file path, or for report checking and refining.
# Replacing Type
1. Find all placeholders
2. When replacing the chart path placeholder, use a relative path. ** src="/workspace/visualization/chart_name.html" **
3. When replacing the text placeholders, generate a detailed text description.
   **When filling in the key insights below the charts, the insights must correspond with those previously added by the add insight tool.**

## Notice:
Use the absolute path starting with /workspace, for example, **/workspace/visualization/chart_name.html**

# Check_refine Type:
1. Check the entire html file
- Have all placeholders been filled?
- Whether the path of the chart is: /workspace/visualization/***.html
- If text-related placeholders still exist, please fill them in as much as possible. If chart path placeholders still exist, please delete that chart part of the report.
   **When filling in the key insights below the charts, the insights must correspond with those previously added by the add insight tool.**



## Output Requirements
1. Generate **report.html** file
2. Print the file path: print(report_path)
3. Make sure the HTML includes Bootstrap for responsive design
""",
            },
        },
        "required": ["code", "code_type"],
    }
