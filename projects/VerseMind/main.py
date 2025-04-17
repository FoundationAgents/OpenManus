"""VerseMind 主程序入口

这个模块是VerseMind项目的主入口，用于启动和运行AI诗歌比赛。
"""

import asyncio
from pathlib import Path
from typing import List

from logger_config import get_logger
from poetry_contest import AIPoetryContest, Poet
from poetry_llm import PoetryLLM

from config import PoetryContestConfig


# 获取日志记录器
logger = get_logger(__name__)

# 可用的模型列表
AVAILABLE_MODELS = [
    "deepseek_ollama",
    "deepseek_v3",
    "deepseek_r1",
    "llama3_2-vision",
    "gemma3",
    "phi4",
    "mistral",
    "Qwen_siliconflow",
]


async def initialize_poets(config: PoetryContestConfig) -> List[Poet]:
    """初始化诗人列表

    Args:
        config: 比赛配置

    Returns:
        List[Poet]: 诗人列表
    """
    poets = []

    # 创建诗人实例
    for model_name in AVAILABLE_MODELS:
        try:
            model = PoetryLLM(model_name)
            poet = Poet(name=f"Poet_{len(poets)+1}", model_name=model_name, model=model)
            poets.append(poet)
            logger.info(f"已初始化诗人: {poet.name} (使用模型: {model_name})")
        except Exception as e:
            logger.error(f"初始化诗人失败 (模型: {model_name}): {e}")

    return poets[: config.num_poets]  # 限制诗人数量


async def main():
    """主函数"""
    try:
        # 创建配置
        config = PoetryContestConfig(
            theme="人机共生",  # 设置比赛主题
            num_poets=8,  # 设置参与比赛的诗人数量
            debug_mode=False,  # 设置是否开启调试模式
        )

        # 初始化诗人列表
        poets = await initialize_poets(config)
        if not poets:
            logger.error("没有可用的诗人，程序退出")
            return

        # 创建结果目录
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)

        # 创建比赛实例
        contest = AIPoetryContest(
            theme=config.theme, poets=poets, results_dir=results_dir
        )

        # 运行比赛
        logger.info("开始运行比赛...")
        success = await contest.run()

        if success:
            # 宣布结果
            contest.announce_results()
            logger.info("比赛已成功完成")
        else:
            logger.error("比赛运行失败")

    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        raise


if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())
