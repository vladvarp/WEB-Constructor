import logging

from main import configure_startup_logging, is_existing_instance


def test_startup_logging_creates_log_file(tmp_path) -> None:
    log_file = tmp_path / "logs" / "application.log"

    configure_startup_logging(log_file)
    logging.getLogger("web_constructor.startup").info("startup marker")

    for handler in logging.getLogger().handlers:
        handler.flush()

    assert log_file.exists()
    assert "startup marker" in log_file.read_text(encoding="utf-8")


def test_existing_mutex_is_detected() -> None:
    assert is_existing_instance(183) is True
    assert is_existing_instance(0) is False
    assert is_existing_instance(5) is False
