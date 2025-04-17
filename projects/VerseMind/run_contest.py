"""诗歌比赛运行脚本"""

import io
from contextlib import redirect_stderr


# 临时重定向stderr以抑制FAISS的GPU警告
with redirect_stderr(io.StringIO()):
    pass

import asyncio
from pathlib import Path

from logger_config import get_logger
from poetry_contest import AIPoetryContest, Poet
from poetry_llm import PoetryLLM


# 获取日志记录器
logger = get_logger(__name__)


def get_theme_from_prompt():
    """从提示词中获取主题"""
    try:
        # 读取参考内容文件
        reference_file = Path(__file__).parent / "prompts" / "reference_content.txt"
        with open(reference_file, "r", encoding="utf-8") as f:
            theme = f.read().strip()
            # 不再显示参考内容，避免重复
            return theme
    except Exception as e:
        logger.error(f"读取主题失败: {e}")
        return None


async def main():
    """主函数"""
    try:
        # 配置日志级别
        PoetryLLM.configure_logging()

        # 获取主题
        theme = get_theme_from_prompt()
        if not theme:
            return

        # 创建诗人列表
        poet_dicts = PoetryLLM.create_poets()
        if not poet_dicts:
            logger.error("未创建任何诗人")
            return

        # 将字典转换为Poet对象
        poets = []
        for poet_dict in poet_dicts:
            try:
                poet = Poet(
                    name=poet_dict["name"],
                    model_name=poet_dict["model_name"],
                    model=PoetryLLM(config_name=poet_dict["model_name"]),
                )
                poets.append(poet)
            except Exception as e:
                logger.error(f"创建诗人 {poet_dict['name']} 失败: {e}")
                continue

        logger.info(f"已创建 {len(poets)} 位诗人")

        # 创建比赛实例
        contest = AIPoetryContest(
            theme=theme, poets=poets, results_dir=Path(__file__).parent / "results"
        )

        # 运行比赛
        if not await contest.run():
            return

        # 宣布结果
        if not contest.announce_results():
            logger.error("宣布比赛结果失败")

    except Exception as e:
        logger.error(f"比赛运行失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
