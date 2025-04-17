"""诗歌比赛配置模块"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import tomli
from exceptions import PromptError


# 评分标准
SCORING_CRITERIA = """评分标准：
1. 意象运用（30%）
2. 语言表达（20%）
3. 情感深度（30%）
4. 结构完整性（20%）"""

# 创作提示词
CREATION_PROMPT = """你是一位才华横溢的诗人。请根据以下主题创作一首诗：

主题：{theme}

要求：
1. 诗歌要符合主题，表达深刻的思想和情感
2. 语言要优美，意境要深远
3. 结构要完整，韵律要和谐
4. 字数在50-100字之间

请直接输出诗歌内容，不要包含任何其他文字。"""

# 评分提示词
SCORING_PROMPT = """请对以下诗歌进行评分和分析：

诗歌内容：
{poem}

{scoring_criteria}

请按照以下格式输出：
评分：[1-10分，整数]
总体评价：[包含优点分析、不足指出、改进建议和总体评价]

详细分析：
- 意象运用：[评分及分析]
- 语言表达：[评分及分析]
- 情感深度：[评分及分析]
- 结构完整性：[评分及分析]"""

logger = logging.getLogger(__name__)


def load_model_configs() -> Dict[str, Any]:
    """从 config.toml 加载模型配置

    Returns:
        Dict[str, Any]: 模型配置字典
    """
    try:
        # 获取 OpenManus 根目录
        openmanus_root = Path(__file__).parent.parent.parent
        config_path = openmanus_root / "config" / "config.toml"

        if not config_path.exists():
            logger.warning(f"配置文件不存在: {config_path}")
            return {}

        with open(config_path, "rb") as f:
            config = tomli.load(f)

        # 获取 LLM 配置
        llm_configs = config.get("llm", {})
        logger.info(f"成功加载 {len(llm_configs)} 个模型配置")
        return llm_configs

    except Exception as e:
        logger.error(f"加载模型配置失败: {e}")
        return {}


@dataclass
class PoetryContestConfig:
    """诗歌比赛配置类"""

    theme: str
    num_poets: int = 5
    debug_mode: bool = False

    # 评分标准
    scoring_criteria = SCORING_CRITERIA

    # 创作提示词模板
    creation_prompt = CREATION_PROMPT

    # 评分提示词模板
    scoring_prompt = SCORING_PROMPT

    # 模型配置
    model_configs: Dict[str, Any] = field(default_factory=load_model_configs)

    def get_creation_prompt(self) -> str:
        """获取创作提示词

        Returns:
            str: 创作提示词
        """
        return self.creation_prompt.format(theme=self.theme)

    def get_scoring_prompt(self, poem: str) -> str:
        """获取评分提示词

        Args:
            poem: 要评分的诗歌

        Returns:
            str: 评分提示词

        Raises:
            PromptError: 提示词错误
        """
        try:
            return self.scoring_prompt.format(
                poem=poem, scoring_criteria=self.scoring_criteria
            )
        except Exception as e:
            raise PromptError(f"生成评分提示词失败: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            "theme": self.theme,
            "num_poets": self.num_poets,
            "debug_mode": self.debug_mode,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PoetryContestConfig":
        """从字典创建配置

        Args:
            data: 配置字典

        Returns:
            PoetryContestConfig: 配置对象
        """
        return cls(
            theme=data["theme"],
            num_poets=data.get("num_poets", 5),
            debug_mode=data.get("debug_mode", False),
        )
