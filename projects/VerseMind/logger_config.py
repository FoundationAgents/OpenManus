"""日志配置模块"""

import logging
import sys


class LevelFormatter(logging.Formatter):
    """根据日志级别使用不同格式的格式化器"""

    def format(self, record):
        # 对于 INFO 级别，使用简单格式
        if record.levelno == logging.INFO:
            self._style._fmt = "%(message)s"
        # 对于 WARNING 和 ERROR 级别，使用完整格式
        else:
            self._style._fmt = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        return super().format(record)


# 创建根日志记录器
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# 创建自定义格式化器
formatter = LevelFormatter()
console_handler.setFormatter(formatter)

# 添加处理器到根日志记录器
logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        logging.Logger: 日志记录器实例
    """
    return logging.getLogger(name)
