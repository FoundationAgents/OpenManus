"""自定义异常类"""


class PoetryContestError(Exception):
    """诗歌比赛基础异常类"""


class ModelConfigError(PoetryContestError):
    """模型配置错误"""


class ModelInitializationError(PoetryContestError):
    """模型初始化错误"""


class PromptError(PoetryContestError):
    """提示词错误"""


class EvaluationError(PoetryContestError):
    """评估错误"""
