import logging
from pathlib import Path

from main import configure_startup_logging, is_existing_instance


def test_startup_logging_creates_log_file(tmp_path) -> None:
    log_file = tmp_path / "logs" / "application.log"
    root_logger = logging.getLogger()

    configure_startup_logging(log_file)
    logging.getLogger("web_constructor.startup").info("startup marker")

    handlers = [
        handler
        for handler in root_logger.handlers
        if isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename).resolve() == log_file.resolve()
    ]
    try:
        for handler in handlers:
            handler.flush()

        assert log_file.exists()
        assert "startup marker" in log_file.read_text(encoding="utf-8")
    finally:
        for handler in handlers:
            root_logger.removeHandler(handler)
            handler.close()


def test_existing_mutex_is_detected() -> None:
    assert is_existing_instance(183) is True
    assert is_existing_instance(0) is False
    assert is_existing_instance(5) is False
