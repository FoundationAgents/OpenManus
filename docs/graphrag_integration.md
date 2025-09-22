# GraphRAG Query Tool Integration

## 概述

GraphRAG Query Tool 已成功集成到 OpenManus MCP 服务器中，允许通过 MCP 协议查询您的 GraphRAG 知识库。

## 功能特性

- **多种查询方法**: 支持 global、local、drift、basic 四种查询方法
- **灵活参数配置**: 支持自定义根路径、社区级别、响应类型等参数
- **异步执行**: 使用异步方式执行 GraphRAG 查询，不阻塞其他操作
- **错误处理**: 完善的错误处理和日志记录

## 工具参数

### 必需参数
- `query` (string): 要在知识库中搜索的查询字符串

### 可选参数
- `method` (string): 搜索方法，可选值：
  - `global`: 全局搜索（默认）
  - `local`: 本地搜索
  - `drift`: 漂移搜索
  - `basic`: 基础搜索
- `root_path` (string): GraphRAG 目录的根路径（默认: "./yh_rag"）
- `community_level` (integer): 全局搜索的社区级别，范围 0-4（默认: 2）
- `response_type` (string): 响应格式类型，可选值：
  - `Multiple Paragraphs`（默认）
  - `Single Paragraph`
  - `Single Sentence`
  - `List of 3-7 Points`
  - `Real Time`

## 使用示例

### 1. 基本查询
```json
{
  "query": "股票投资的道天地将法是啥意思？"
}
```

### 2. 指定查询方法
```json
{
  "query": "股票投资的道天地将法是啥意思？",
  "method": "local"
}
```

### 3. 完整参数查询
```json
{
  "query": "股票投资的道天地将法是啥意思？",
  "method": "global",
  "root_path": "./yh_rag",
  "community_level": 3,
  "response_type": "List of 3-7 Points"
}
```

## 安装和配置

### 1. 安装依赖
确保安装了 GraphRAG：
```bash
pip install graphrag~=0.4.1
```

### 2. 配置环境
确保 `yh_rag/.env` 文件包含必要的 API 密钥：
```
GRAPHRAG_API_KEY=your_api_key_here
```

### 3. 验证配置
确保 `yh_rag/settings.yaml` 配置正确，包含正确的模型和 API 端点配置。

## MCP 服务器集成

工具已自动注册到 MCP 服务器中，工具名称为 `graphrag_query`。

### 启动 MCP 服务器
```bash
cd /path/to/OpenManus
python app/mcp/server.py
```

### 通过 MCP 客户端调用
工具将作为 `graphrag_query` 函数可用，支持上述所有参数。

## 错误处理

工具包含完善的错误处理：
- 参数验证
- GraphRAG 命令执行错误捕获
- 详细的错误信息返回
- 日志记录

## 注意事项

1. **环境要求**: 确保 Python 环境中安装了 GraphRAG 及其依赖
2. **路径配置**: 确保 `root_path` 指向正确的 GraphRAG 工作目录
3. **API 配置**: 确保 `.env` 文件中的 API 密钥有效
4. **数据准备**: 确保 GraphRAG 知识库已经构建完成

## 故障排除

### 常见问题

1. **"No module named graphrag"**
   - 解决方案: 安装 GraphRAG: `pip install graphrag`

2. **"GraphRAG query failed"**
   - 检查 API 密钥是否正确
   - 检查网络连接
   - 检查 GraphRAG 配置文件

3. **"No results found"**
   - 检查查询字符串是否合适
   - 尝试不同的查询方法
   - 确认知识库数据是否存在

## 扩展功能

未来可以考虑添加的功能：
- 批量查询支持
- 查询结果缓存
- 自定义提示词模板
- 查询历史记录
- 结果格式化选项