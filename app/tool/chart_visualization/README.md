

# Chart Visualization Tool

The chart visualization tool generates data processing code through Python and ultimately invokes [@visactor/vmind](https://github.com/VisActor/VMind) to obtain chart specifications. Chart rendering is implemented using [@visactor/vchart](https://github.com/VisActor/VChart).

## Installation

1. Install Node.js >= 18

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
# After installation, restart the terminal and install the latest Node.js LTS version:
nvm install --lts
```

2. Install dependencies

```bash
cd app/tool/chart_visualization
npm install
```

## Tool
### python_execute

Execute the necessary parts of data analysis (excluding data visualization) using Python code, including data processing, data summary, report generation, and some general Python script code.

#### Input
```typescript
{
  // Code type: data processing/data report/other general tasks
  code_type: "process" | "report" | "others"
  // Final execution code
  code: string;
}
```

#### Output
Python execution results, including the saving of intermediate files and print output results.

### visualization_preparation

A pre-tool for data visualization with two purposes,

#### Data -> Chart
Used to extract the data needed for analysis (.csv) and the corresponding visualization description from the data, ultimately outputting a JSON configuration file.

#### Chart + Insight -> Chart
Select existing charts and corresponding data insights, choose data insights to add to the chart in the form of data annotations, and finally generate a JSON configuration file.

#### Input
```typescript
{
  // Code type: data visualization or data insight addition
  code_type: "visualization" | "insight"
  // Python code used to produce the final JSON file
  code: string;
}
```

#### Output
A configuration file for data visualization, used for the `data_visualization tool`.

## data_visualization

Generate specific data visualizations based on the content of `visualization_preparation`.

### Input
```typescript
{
  // Configuration file path
  json_path: string;
  // Current purpose, data visualization or insight annotation addition
  tool_type: "visualization" | "insight";
  // Final product png or html; html supports vchart rendering and interaction
  output_type: 'png' | 'html'
  // Language, currently supports Chinese and English
  language: "zh" | "en"
}
```

## VMind Configuration

### LLM

VMind requires LLM invocation for intelligent chart generation. By default, it uses the `config.llm["default"]` configuration.

### Generation Settings

Main configurations include chart dimensions, theme, and generation method:
### Generation Method
Default: png. Currently supports automatic selection of `output_type` by LLM based on context.

### Dimensions
Default dimensions are unspecified. For HTML output, charts fill the entire page by default. For PNG output, defaults to `1000*1000`.

### Theme
Default theme: `'light'`. VChart supports multiple themes. See [Themes](https://www.visactor.io/vchart/guide/tutorial_docs/Theme/Theme_Extension).

## Test

Currently, three tasks of different difficulty levels are set for testing.

### Simple Chart Generation Task

Provide data and specific chart generation requirements, test results, execute the command:
```bash
python -m app.tool.chart_visualization.test.chart_demo
```
The results should be located under `workspace\visualization`, involving 9 different chart results.

### Simple Data Report Task

Provide simple raw data analysis requirements, requiring simple processing of the data, execute the command:
```bash
python -m app.tool.chart_visualization.test.report_demo
```
The results are also located under `workspace\visualization`.
