from app.tool.chart_visualization.python_execute import NormalPythonExecute

class ReportBeautify(NormalPythonExecute):
    """A tool for transforming a basic health report into a professional, visually appealing final version"""

    name: str = "report_beautify"
    description: str = """
    This tool should be called **LAST** in the workflow to perform final beautification of the data report.
    It will:
    1. Apply advanced styling and layout enhancements
    2. Add interactive elements and visual polish
    3. Ensure mobile responsiveness

    Key beautification features to implement:
    - colorful and fancy background and color scheme
    - Modern CSS styling with gradients and shadows
    - Font Awesome icons for visual cues
    - Animated progress bars for metrics
    - Card-based layout with hover effects
    - Responsive design for all devices
    - Scroll-triggered animations
    - Professional typography hierarchy

    ## Output Requirements
    1. Generate **beautify_report.html** file
    2. Print the file path: print(report_path)
    """

    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": """
                Python code that beautify the report:
                1. CSS/JS enhancements for modern styling
                2. Structure optimization for better readability
                3. Mobile responsiveness adjustments

                Example tasks:
                - Add Bootstrap 5 + Font Awesome
                - Add metric cards with progress bars
                - Create responsive tables
                """,
            },
        },
        "required": ["code"],
    }
