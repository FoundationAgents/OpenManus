import asyncio
import sys
from pathlib import Path


# 获取 OpenManus 根目录
openmanus_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(openmanus_root))

from app.agent.manus import Manus
from app.logger import logger


# 测试用的提示词
TEST_PROMPT = "写一首关于人工智能的诗"

# 要测试的 LLM 配置列表
LLM_CONFIGS = [
    {"name": "默认 DeepSeek R1", "config": "llm"},
    {"name": "Ollama DeepSeek", "config": "llm.ollama"},
    {"name": "Gemma 4B", "config": "llm.gemma"},
    {"name": "Phi 4", "config": "llm.phi"},
    {"name": "Mistral", "config": "llm.mistral"},
    {"name": "DeepSeek API", "config": "llm.deepseek_api"},
]


async def test_poetry_creation():
    """测试诗歌创作"""
    for llm_config in LLM_CONFIGS:
        logger.info(f"Testing with {llm_config['name']}")
        agent = Manus(llm_config=llm_config["config"])
        try:
            response = await agent.run(TEST_PROMPT)
            print(f"\n{llm_config['name']} 的创作结果:")
            print(response)
        except Exception as e:
            logger.error(f"Error with {llm_config['name']}: {e}")


async def main():
    """主函数"""
    try:
        await test_poetry_creation()
    except KeyboardInterrupt:
        logger.warning("测试被中断")
    except Exception as e:
        logger.error(f"测试出错: {e}")


if __name__ == "__main__":
    asyncio.run(main())
