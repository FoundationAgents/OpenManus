from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.config import config
from app.prompt.visualization import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tool import Terminate, ToolCollection
from app.tool.chart_visualization.python_execute import NormalPythonExecute
# from app.tool.chart_visualization.chart_prepare import VisualizationPrepare
# from app.tool.chart_visualization.data_visualization import DataVisualization
# from app.tool.chart_visualization.initial_report_generation import GenerateInitialReport
# from app.tool.chart_visualization.final_report_generation import GenerateFinalReport
# from app.tool.chart_visualization.search_report_template import SearchReportTemplate
# from app.tool.chart_visualization.report_template_generation import ReportTemplateGeneration
# from app.tool.chart_visualization.initial_information_collection import InitialInformationCollection
from app.tool.chart_visualization.chart_prepare import VisualizationPrepare
from app.tool.chart_visualization.select_insights import SelectInsights
from app.tool.chart_visualization.add_insights import AddInsights
from app.tool.chart_visualization.data_visualization import DataVisualization
from app.tool.chart_visualization.v2.search_html_library import SearchHtmlLibrary
from app.tool.chart_visualization.v2.initial_report_generation import GenerateInitialReport
from app.tool.chart_visualization.v2.report_template_generation import ReportTemplateGeneration
from app.tool.chart_visualization.v2.final_report_generation import GenerateFinalReport
from app.tool.chart_visualization.v2.report_beautify import ReportBeautify


class DataAnalysis(ToolCallAgent):
    """
    A data analysis agent that uses planning to solve various data analysis tasks.

    This agent extends ToolCallAgent with a comprehensive set of tools and capabilities,
    including Data Analysis, Chart Visualization, Data Report.
    """

    name: str = "Data_Analysis"
    description: str = """
    A data science agent specializing in Python-based analytics and advanced visualization techniques
    for solving complex data analysis challenges.

    Standard Report Generation Workflow:
    1. Template Preparation:
       - SearchHtmlLibrary: Identify suitable visualization templates
       - ReportTemplateGeneration & GenerateInitialReport: Create initial report structure

    2. Visualization Pipeline:
       - VisualizationPrepare: Configure data for visualization
       - DataVisualization: Generate interactive charts and graphs

    3. Insight Enhancement:
       - SelectInsights: Extract key findings from visualizations
       - AddInsights: Annotate charts with analytical insights

    4. Report Finalization:
       - GenerateFinalReport: Replace the placeholders with charts
       - ReportBeautify: Apply professional styling and formatting

    Operational Protocol:
    - First determine optimal visualization types based on dataset characteristics
    - Utilize HTML template library to establish report framework
    - Execute visualization pipeline to create data representations
    - Enhance each chart with key insights you selected
    - Assemble final report by embedding enriched visualizations
    """

    system_prompt: str = SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 15000
    max_steps: int = 20

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            NormalPythonExecute(),
            SearchHtmlLibrary(),
            ReportTemplateGeneration(),
            GenerateInitialReport(),
            GenerateFinalReport(),
            ReportBeautify(),
            AddInsights(),
            VisualizationPrepare(),
            DataVisualization(),
            SelectInsights(),
            Terminate(),
        )
    )
