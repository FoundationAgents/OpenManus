import logging
import sys
from datetime import datetime
from importlib.util import find_spec
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


if find_spec("loguru") is not None:
    from loguru import logger as _logger  # type: ignore[import-not-found]

    _loguru_available = True
else:  # pragma: no cover - loguru expected in production environments
    _loguru_available = False
    _logger = logging.getLogger("app")


_print_level = "INFO"


def define_log_level(
    print_level: str = "INFO", logfile_level: str = "DEBUG", name: str | None = None
):
    """Configure the application logger with sane defaults.

    Uses *loguru* when available for richer logging capabilities while
    gracefully falling back to the standard :mod:`logging` module when the
    dependency is missing (for example in lightweight environments).
    """

    global _print_level
    _print_level = print_level

    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y%m%d%H%M%S")
    log_name = f"{name}_{formatted_date}" if name else formatted_date

    log_dir: Path = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    if _loguru_available:
        _logger.remove()
        _logger.add(sys.stderr, level=print_level)
        _logger.add(log_dir / f"{log_name}.log", level=logfile_level)
    else:
        _logger.setLevel(getattr(logging, logfile_level.upper(), logging.DEBUG))

        for handler in list(_logger.handlers):
            _logger.removeHandler(handler)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setLevel(getattr(logging, print_level.upper(), logging.INFO))
        stream_handler.setFormatter(formatter)

        file_handler = logging.FileHandler(log_dir / f"{log_name}.log")
        file_handler.setLevel(getattr(logging, logfile_level.upper(), logging.DEBUG))
        file_handler.setFormatter(formatter)

        _logger.addHandler(stream_handler)
        _logger.addHandler(file_handler)

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
