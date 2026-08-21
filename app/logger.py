import sys

from loguru import logger as _logger

from app.config import PROJECT_ROOT


_print_level = "INFO"


def define_log_level(print_level="INFO", logfile_level="DEBUG", name: str = None):
    """Adjust the log level to above level"""
    global _print_level
    _print_level = print_level

    log_name = name or "openmanus"

    _logger.remove()
    _logger.add(sys.stderr, level=print_level)
    _logger.add(
        PROJECT_ROOT / f"logs/{log_name}_{{time:YYYYMMDD}}.log",
        level=logfile_level,
        rotation="00:00",
        retention="7 days",
    )
    return _logger


logger = define_log_level()


if __name__ == "__main__":
    logger.info("Starting application")
    logger.debug("Debug message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
