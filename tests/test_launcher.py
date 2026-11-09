import logging
from pathlib import Path
from unittest.mock import patch

from main import (
    configure_startup_logging,
    get_venv_python,
    is_existing_instance,
    prepare_virtual_environment,
)


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


def test_prepare_environment_creates_venv_and_installs_requirements(tmp_path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("fastapi>=0.115,<1.0\n", encoding="utf-8")
    interpreter = get_venv_python(tmp_path / ".venv")

    with (
        patch("main.venv.EnvBuilder.create") as create_venv,
        patch("main.subprocess.run") as run,
        patch("main._requirements_imports_available", return_value=False),
        patch("main.get_venv_python", return_value=interpreter),
        patch("main.get_venv_gui_python", return_value=interpreter),
    ):
        def create_environment(path):
            interpreter.parent.mkdir(parents=True, exist_ok=True)
            interpreter.touch()

        create_venv.side_effect = create_environment
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        run.return_value.stderr = ""

        _, should_relaunch = prepare_virtual_environment(
            tmp_path
        )

    create_venv.assert_called_once()
    run.assert_called_once()
    assert should_relaunch is True
    assert (tmp_path / ".venv" / ".requirements.sha256").is_file()


def test_prepare_environment_skips_pip_when_requirements_are_current(tmp_path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("fastapi>=0.115,<1.0\n", encoding="utf-8")
    venv_dir = tmp_path / ".venv"
    interpreter = get_venv_python(venv_dir)
    venv_dir.mkdir()
    interpreter.parent.mkdir(parents=True)
    interpreter.touch()
    import hashlib

    marker = venv_dir / ".requirements.sha256"
    marker.write_text(
        hashlib.sha256(requirements.read_bytes()).hexdigest(), encoding="ascii"
    )

    with (
        patch("main._requirements_imports_available", return_value=True),
        patch("main.get_venv_python", return_value=interpreter),
        patch("main.get_venv_gui_python", return_value=interpreter),
        patch("main.subprocess.run") as run,
    ):
        _, should_relaunch = prepare_virtual_environment(
            tmp_path
        )

    run.assert_not_called()
    assert should_relaunch is True
