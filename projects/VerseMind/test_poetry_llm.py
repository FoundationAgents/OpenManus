"""测试诗歌LLM类"""

from pathlib import Path

import pytest
from poetry_llm import PoetryLLM, get_available_models, get_model_config


@pytest.fixture
def poetry_llm():
    """创建PoetryLLM实例"""
    return PoetryLLM(config_name="llm", llm_config={})


def test_get_available_models():
    """测试获取可用模型"""
    models = get_available_models()
    assert len(models) > 0
    assert all(isinstance(model[0], str) for model in models)
    assert all(isinstance(model[1], str) for model in models)


def test_get_model_config():
    """测试获取模型配置"""
    config = get_model_config("llm")
    assert config is not None
    assert "model" in config
    assert "api_type" in config


@pytest.mark.asyncio
async def test_create_poem(poetry_llm):
    """测试创作诗歌"""
    theme = "春天"
    poem = await poetry_llm.create_poem(theme)
    assert poem is not None
    assert "##" in poem  # 检查是否包含标题
    assert "创作思路说明：" in poem  # 检查是否包含创作思路


@pytest.mark.asyncio
async def test_evaluate_poem(poetry_llm):
    """测试评估诗歌"""
    poem = """## 春天的早晨
春风轻拂面，
花香满园中。
蝴蝶翩翩舞，
阳光暖融融。

创作思路说明：这首诗描绘了春天早晨的美好景象，通过春风、花香、蝴蝶和阳光等意象，展现了春天的生机与活力。"""

    theme = "春天"
    result = await poetry_llm.evaluate_poem(poem, theme)
    assert result is not None
    assert "dimensions" in result
    assert "comments" in result


def test_prompt_file_exists():
    """测试提示词文件是否存在"""
    prompt_file = Path(__file__).parent / "prompts" / "creation_prompt.txt"
    assert prompt_file.exists()

    scoring_file = Path(__file__).parent / "prompts" / "scoring_prompt.txt"
    assert scoring_file.exists()
