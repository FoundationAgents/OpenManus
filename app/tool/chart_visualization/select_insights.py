from app.tool.chart_visualization.python_execute import NormalPythonExecute
class SelectInsights(NormalPythonExecute):
    name: str = "insights_selection"
    description: str = (
        "This tool analyzes data_visualization tool's outputs and identifies key data insights for each chart."
        "based on their importance ranking. Insights are prioritized in three tiers:\n"
        "1 **Critical Insights**: 'abnormal_trend', 'abnormal_band', 'turning_point', 'overall_trend'\n"
        "2 **Important Insights**: 'outlier', 'extreme_value', 'majority_value', 'avg'\n"
        "3 **Basic Insights**: 'min', 'max'\n\n"
        "**!Must be called immediately after data_visualization completes!**"
        "**!All insights_id must come from the data_visualization analysis results!**"

    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": """Python code to analyze visualized charts and extract insights.

# PRIORITY REQUIREMENTS
Insights must be selected and ranked according to these importance tiers:
1. **First Priority**: Always include 'abnormal_trend', 'abnormal_band', 'turning_point', 'overall_trend' when present
2. **Second Priority**: Include 'outlier', 'extreme_value', 'majority_value', 'avg' if no first-tier insights exist
3. **Third Priority**: Fall back to 'min', 'max' only when no higher-priority insights are available

# EXECUTION REQUIREMENTS
1. **Timing**: MUST be called immediately after data_visualization completes
2. **Dependency**: MUST use insights from data_visualization output as the only source for insights_id


# CODE REQUIREMENTS
Your Python code must:
1. Analyze the data_visualization results to identify significant insights for each chart.
2. Save the findings in JSON format:
   ```json
   [
    {
     "chartPath": "string",  // Path to the generated chart
     "insights_id": number[] // Array of key insight IDs FROM DATA_VISUALIZATION RESULTS
    },
    {
     "chartPath": "string",  // Path to the generated chart
     "insights_id": number[] // Array of key insight IDs FROM DATA_VISUALIZATION RESULTS
    },
    ...
    ]
    ```
Json file saving in utf-8 with path print: print(json_path)
""",
            },
        },
        "required": ["code"],
    }
