# Test data for GraphRAG query tool tests

SAMPLE_QUERIES = [
    "股票投资的道天地将法是啥意思？",
    "什么是投资策略？",
    "如何进行风险管理？",
    "价值投资的核心理念是什么？",
    "技术分析的基本原理",
]

SAMPLE_RESPONSES = {
    "global": {
        "success": """
根据知识库中的信息，股票投资的"道天地将法"是一个投资理念框架：

道：投资的根本原则和哲学思想
天：市场环境和宏观经济因素
地：具体的投资标的和行业分析
将：投资者的能力和经验
法：具体的投资方法和策略

这个框架强调投资需要从多个维度进行综合考虑。
        """.strip(),
        "empty": "",
        "error": "GraphRAG query failed: Configuration error",
    },
    "local": {
        "success": """
在本地搜索中找到相关信息：

投资策略是指投资者为实现投资目标而制定的具体行动方案，包括资产配置、风险控制、时机选择等方面的规划。
        """.strip(),
        "empty": "",
        "error": "GraphRAG query failed: Local search index not found",
    },
}

MOCK_COMMAND_OUTPUTS = {
    "help_success": "GraphRAG CLI tool\n\nUsage: python -m graphrag [OPTIONS] COMMAND [ARGS]...",
    "help_error": "python: No module named 'graphrag'",
    "query_success": SAMPLE_RESPONSES["global"]["success"],
    "query_error": "Error: Invalid configuration file",
}

# Mock file system structure for yh_rag
MOCK_YH_RAG_STRUCTURE = {
    "settings.yaml": """
llm:
  api_key: test_key
  type: openai_chat
  model: gpt-4

embeddings:
  llm:
    api_key: test_key
    type: openai_embedding
    model: text-embedding-ada-002

input:
  type: file
  file_type: text
  base_dir: "input"

storage:
  type: file
  base_dir: "output"
""",
    "input/sample.txt": "This is a sample document for testing GraphRAG functionality.",
    "output/.gitkeep": "",
    ".env": """
GRAPHRAG_API_KEY=test_key
GRAPHRAG_LLM_TYPE=openai_chat
GRAPHRAG_LLM_MODEL=gpt-4
""",
}
