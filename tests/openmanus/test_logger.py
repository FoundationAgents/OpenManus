from typing import Any, Callable

from pytest_loguru.plugin import caplog  # noqa: F401


def test_logger(caplog):
    from app.logger import logger

    messages: list[str] = []

    def hooked_logged(method: Callable[[str], Any]):
        def wrapper(message: str):
            messages.append(message)
            method(message)

        return wrapper

    hooked_logged(logger.debug)("debug message")
    hooked_logged(logger.info)("info message")
    hooked_logged(logger.warning)("warning message")
    hooked_logged(logger.error)("error message")
    hooked_logged(logger.critical)("critical message")

    logger.complete()
    captured = caplog.text

    for message in messages:
        assert (
            message in captured
        ), f"{repr(message)} not found in captured output. {captured=}"
