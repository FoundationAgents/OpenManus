# 图表可视化工具

图表可视化工具，通过python生成数据处理代码，最终调用[@visactor/vmind](https://github.com/VisActor/VMind)得到图表的spec结果，图表渲染使用[@visactor/vchart](https://github.com/VisActor/VChart)

## 安装(Mac / Linux)

1. 安装node >= 18

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
# 激活nvm，以Bash为例
source ~/.bashrc
# 然后安装 Node 最近一个稳定颁布
nvm install node
# 激活使用，例如最新一个稳定颁布为22，则use 22
nvm use 22
```

2. 安装依赖

```bash
cd app/tool/chart_visualization
npm install
```

## 安装(Windows)
1. 安装nvm-windows

    从[github官网](https://github.com/coreybutler/nvm-windows?tab=readme-ov-file#readme)上下载最新版本`nvm-setup.exe`并且安装

2. 使用nvm安装node

```powershell
# 然后安装 Node 最近一个稳定颁布
nvm install node
# 激活使用，例如最新一个稳定颁布为22，则use 22
nvm use 22
```

3. 安装依赖

```bash
# 在当前仓库下定位到相应位置
cd app/tool/chart_visualization
npm install
```
## Tool
### python_execute

用python代码执行数据分析（除数据可视化以外）中需要的部分，包括数据处理，数据总结摘要，报告生成以及一些通用python脚本代码

#### 输入
```typescript
{
  // 代码类型：数据处理/数据报告/其他通用任务
  code_type: "process" | "report" | "others"
  // 最终执行代码
  code: string;
}
```

#### 输出
python执行结果，带有中间文件的保存和print输出结果

### visualization_preparation

数据可视化前置工具，有两种用途，

#### Data -〉 Chart
用于从数据中提取需要分析的数据(.csv)和对应可视化的描述，最终输出一份json配置文件。

#### Chart + Insight -> Chart
选取已有的图表和对应的数据洞察，挑选数据洞察以数据标注的形式增加到图表中，最终生成一份json配置文件。

#### 输入
```typescript
{
  // 代码类型：数据可视化 或者 数据洞察添加
  code_type: "visualization" | "insight"
  // 用于生产最终json文件的python代码
  code: string;
}
```

#### 输出
数据可视化的配置文件，用于`data_visualization tool`


## data_visualization

根据`visualization_preparation`的内容，生成具体的数据可视化

### 输入
```typescript
{
  // 配置文件路径
  json_path: string;
  // 当前用途，数据可视化或者洞察标注添加
  tool_type: "visualization" | "insight";
  // 最终产物png或者html;html下支持vchart渲染和交互
  output_type: 'png' | 'html'
  // 语言,目前支持中文和英文
  language: "zh" | "en"
}
```

## 输出
最终以'png'或者'html'的形式保存在本地，输出保存的图表路径以及图表中发现的数据洞察

## VMind配置

### LLM

VMind本身也需要通过调用大模型得到智能图表生成结果，目前默认会使用`config.llm["default"]`配置

### 生成配置

主要生成配置包括图表的宽高、主题以及生成方式；
### 生成方式
默认为png，目前支持大模型根据上下文自己选择`output_type`

### 宽高
目前默认不指定宽高，`html`下默认占满整个页面，'png'下默认为`1000 * 1000`

### 主题
目前默认主题为`'light'`，VChart图表支持多种主题，详见[主题](https://www.visactor.io/vchart/guide/tutorial_docs/Theme/Theme_Extension)


## 测试

当前设置了三种不同难度的任务用于测试

### 简单图表生成任务

给予数据和具体的图表生成需求，测试结果，执行命令：
```bash
python -m app.tool.chart_visualization.test.chart_demo
```
结果应位于`worksapce\visualization`下，涉及到9种不同的图表结果

### 简单数据报表任务

给予简单原始数据可分析需求，需要对数据进行简单加工处理，执行命令：
```bash
python -m app.tool.chart_visualization.test.report_demo
```
结果同样位于`worksapce\visualization`下
