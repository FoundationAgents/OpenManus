# GraphRAG 工具测试指南

## 📋 概述

本文档介绍如何测试 GraphRAG 查询工具的功能和集成。我们已经为 `app/tool/graphrag_query.py` 创建了完整的测试套件。

## 🗂️ 测试文件结构

```
tests/
├── conftest.py                    # pytest 配置和 fixtures
├── tool/
│   ├── __init__.py               # 工具测试包初始化
│   ├── test_graphrag_query.py    # GraphRAG 工具主测试文件
│   └── test_data.py              # 测试数据和模拟响应
└── sandbox/                      # 现有的沙盒测试

# 辅助脚本（位于 tests/tool/ 目录）
tests/tool/run_graphrag_tests.py  # 测试运行器
verify_graphrag_tool.py           # 工具验证脚本
test_structure.py                 # 结构验证脚本
```

## 🧪 测试类型

### 1. 结构测试 (Structure Tests)
验证文件结构和基本集成：
```bash
python3 test_structure.py
```

### 2. 单元测试 (Unit Tests)
测试工具的各个功能模块：
```bash
python3 tests/tool/run_graphrag_tests.py unit -v
# 或者从 tests/tool 目录运行：
# cd tests/tool && python3 run_graphrag_tests.py unit -v
```

### 3. 集成测试 (Integration Tests)
测试与实际 GraphRAG 的集成：
```bash
python3 tests/tool/run_graphrag_tests.py integration -v
# 或者从 tests/tool 目录运行：
# cd tests/tool && python3 run_graphrag_tests.py integration -v
```

### 4. 快速测试 (Quick Tests)
运行快速测试，跳过慢速测试：
```bash
python3 tests/tool/run_graphrag_tests.py quick -v
# 或者从 tests/tool 目录运行：
# cd tests/tool && python3 run_graphrag_tests.py quick -v
```

## 🔧 测试环境设置

### 前置条件
1. **安装基础依赖**：
   ```bash
   pip install -r requirements.txt
   ```

2. **安装 GraphRAG**（用于集成测试）：
   ```bash
   pip install graphrag
   ```

3. **安装测试依赖**：
   ```bash
   pip install pytest pytest-asyncio
   ```

### 检查环境
```bash
python3 tests/tool/run_graphrag_tests.py check
# 或者从 tests/tool 目录运行：
# cd tests/tool && python3 run_graphrag_tests.py check
```

## 📝 测试覆盖范围

### TestGraphRAGQuery 类测试

#### 基础功能测试
- ✅ 工具初始化和属性验证
- ✅ 参数模式验证
- ✅ 必需参数检查
- ✅ 无效参数处理

#### 执行测试
- ✅ 成功的全局查询 (global query)
- ✅ 成功的本地查询 (local query)
- ✅ 自定义参数处理
- ✅ 命令失败处理
- ✅ 空结果处理
- ✅ 异常处理

#### 设置验证测试
- ✅ 成功的设置验证
- ✅ 设置验证失败
- ✅ 设置验证异常处理

#### 查询方法测试
- ✅ 所有支持的查询方法 (global, local, drift, basic)

### TestGraphRAGQueryIntegration 类测试

#### 集成测试
- ✅ 实际 GraphRAG 可用性检查
- ✅ 真实 yh_rag 目录测试

## 🎯 测试用例详解

### 1. 参数验证测试
```python
# 测试缺少必需参数
result = await tool.execute()
assert result.error == "Query parameter is required"

# 测试无效方法
result = await tool.execute(query="test", method="invalid")
assert "Invalid method" in result.error
```

### 2. 成功执行测试
```python
# 模拟成功的 GraphRAG 响应
with patch('asyncio.create_subprocess_exec') as mock_subprocess:
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (
        "GraphRAG response".encode('utf-8'), b""
    )
    mock_subprocess.return_value = mock_process
    
    result = await tool.execute(query="测试查询", method="global")
    assert result.error is None
    assert result.output == "GraphRAG response"
```

### 3. 错误处理测试
```python
# 测试命令执行失败
mock_process.returncode = 1
mock_process.communicate.return_value = (
    b"", "Error message".encode('utf-8')
)

result = await tool.execute(query="test")
assert "GraphRAG query failed" in result.error
```

## 🚀 运行测试

### 基本运行
```bash
# 运行所有单元测试
python3 tests/tool/run_graphrag_tests.py unit

# 运行带详细输出的测试
python3 tests/tool/run_graphrag_tests.py unit -v

# 运行带覆盖率报告的测试
python3 tests/tool/run_graphrag_tests.py unit -c

# 或者从 tests/tool 目录运行：
# cd tests/tool
# python3 run_graphrag_tests.py unit -v
```

### 使用 pytest 直接运行
```bash
# 运行特定测试类
python3 -m pytest tests/tool/test_graphrag_query.py::TestGraphRAGQuery -v

# 运行特定测试方法
python3 -m pytest tests/tool/test_graphrag_query.py::TestGraphRAGQuery::test_execute_successful_global_query -v

# 运行所有工具测试
python3 -m pytest tests/tool/ -v
```

## 📊 测试标记 (Markers)

我们使用以下 pytest 标记来分类测试：

- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.slow`: 慢速测试
- `@pytest.mark.requires_graphrag`: 需要 GraphRAG 安装的测试

### 运行特定标记的测试
```bash
# 只运行单元测试（排除集成测试）
python3 -m pytest -m "not integration" tests/tool/

# 只运行快速测试
python3 -m pytest -m "not slow" tests/tool/

# 只运行集成测试
python3 -m pytest -m "integration" tests/tool/
```

## 🔍 调试测试

### 查看详细输出
```bash
python3 -m pytest tests/tool/test_graphrag_query.py -v -s
```

### 运行单个测试进行调试
```bash
python3 -m pytest tests/tool/test_graphrag_query.py::TestGraphRAGQuery::test_execute_successful_global_query -v -s
```

### 使用 pdb 调试
```bash
python3 -m pytest tests/tool/test_graphrag_query.py --pdb
```

## 📈 测试报告

### 生成 HTML 覆盖率报告
```bash
python3 tests/tool/run_graphrag_tests.py unit -c
# 报告将生成在 htmlcov/ 目录中
```

### 生成 JUnit XML 报告
```bash
python3 -m pytest tests/tool/ --junitxml=test_results.xml
```

## 🐛 常见问题

### 1. ModuleNotFoundError: No module named 'pytest'
```bash
pip install pytest pytest-asyncio
```

### 2. GraphRAG 模块未找到
```bash
pip install graphrag
```

### 3. 测试超时
某些集成测试可能需要较长时间，可以增加超时时间：
```bash
python3 -m pytest tests/tool/ --timeout=300
```

### 4. 权限问题
确保测试脚本有执行权限：
```bash
chmod +x tests/tool/run_graphrag_tests.py
chmod +x verify_graphrag_tool.py
chmod +x test_structure.py
```

## 📚 扩展测试

### 添加新的测试用例
1. 在 `tests/tool/test_graphrag_query.py` 中添加新的测试方法
2. 使用 `@pytest.mark.asyncio` 装饰异步测试
3. 使用适当的标记分类测试

### 添加测试数据
在 `tests/tool/test_data.py` 中添加新的测试数据：
```python
NEW_TEST_QUERIES = [
    "新的测试查询",
    # ...
]
```

### 创建新的测试文件
为其他工具创建类似的测试文件：
```bash
tests/tool/test_other_tool.py
```

## ✅ 验证清单

在提交代码前，请确保：

- [ ] 所有结构测试通过：`python3 test_structure.py`
- [ ] 所有单元测试通过：`python3 tests/tool/run_graphrag_tests.py unit`
- [ ] 代码覆盖率达到要求：`python3 tests/tool/run_graphrag_tests.py unit -c`
- [ ] 集成测试通过（如果 GraphRAG 可用）：`python3 tests/tool/run_graphrag_tests.py integration`
- [ ] 没有测试警告或错误
- [ ] 文档已更新

## 🎉 总结

通过这套完整的测试体系，我们可以：

1. **验证工具结构**：确保文件和集成正确
2. **测试核心功能**：验证所有主要功能正常工作
3. **模拟各种场景**：包括成功、失败和边界情况
4. **支持持续集成**：提供自动化测试能力
5. **便于调试**：提供详细的错误信息和调试工具

这确保了 GraphRAG 工具的可靠性和稳定性，为用户提供了高质量的 RAG 查询服务。