from __future__ import annotations

import ctypes
import hashlib
import importlib.util
import logging
import os
import re
import subprocess
import sys
import venv
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_FILE = PROJECT_ROOT / "logs" / "application.log"
MUTEX_NAME = "Local\\WEBConstructor.Application"
ERROR_ALREADY_EXISTS = 183
REQUIREMENTS_MARKER = ".requirements.sha256"

# Distribution names that do not match their import package names.
IMPORT_NAME_OVERRIDES = {
    "pywebview": "webview",
}


def configure_startup_logging(log_file: Path = LOG_FILE) -> None:
    """Initialize application logging before environment setup and imports."""
    log_file = log_file.resolve()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler_exists = any(
        isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename).resolve() == log_file
        for handler in logger.handlers
    )
    if not handler_exists:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(handler)


def get_venv_python(venv_dir: Path) -> Path:
    """Return the virtual environment interpreter for the current platform."""
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def get_venv_gui_python(venv_dir: Path) -> Path:
    """Return pythonw.exe on Windows, or the regular interpreter elsewhere."""
    if os.name == "nt":
        return venv_dir / "Scripts" / "pythonw.exe"
    return get_venv_python(venv_dir)


def _requirements_imports_available(requirements_file: Path) -> bool:
    """Check that each declared runtime distribution has an importable module."""
    for raw_line in requirements_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(("-", "git+", "http:")):
            continue

        match = re.match(r"([A-Za-z0-9_.-]+)", line)
        if not match:
            continue
        distribution = match.group(1).lower().replace("_", "-")
        module = IMPORT_NAME_OVERRIDES.get(
            distribution, distribution.replace("-", "_")
        )
        try:
            if importlib.util.find_spec(module) is None:
                return False
        except (ImportError, ValueError):
            return False
    return True


def prepare_virtual_environment(
    project_root: Path = PROJECT_ROOT,
    current_executable: Path | None = None,
) -> tuple[Path, bool]:
    """
    Create the project venv and install requirements when needed.

    Returns (venv_interpreter, should_relaunch). The requirements hash avoids
    running pip on every normal application start.
    """
    project_root = project_root.resolve()
    requirements_file = project_root / "requirements.txt"
    if not requirements_file.is_file():
        raise FileNotFoundError(f"Не найден файл зависимостей: {requirements_file}")

    venv_dir = project_root / ".venv"
    interpreter = get_venv_python(venv_dir)
    gui_interpreter = get_venv_gui_python(venv_dir)
    marker = venv_dir / REQUIREMENTS_MARKER

    if not interpreter.is_file():
        logging.getLogger("web_constructor.startup").info(
            "Creating virtual environment at %s", venv_dir
        )
        venv.EnvBuilder(with_pip=True).create(venv_dir)

    requirements_hash = hashlib.sha256(
        requirements_file.read_bytes()
    ).hexdigest()
    installed_hash = marker.read_text(encoding="ascii").strip() if marker.is_file() else ""

    if (
        installed_hash != requirements_hash
        or not _requirements_imports_available(requirements_file)
    ):
        logger = logging.getLogger("web_constructor.startup")
        logger.info("Installing or updating application dependencies")
        result = subprocess.run(
            [
                str(interpreter),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(requirements_file),
            ],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout:
            logger.info("Dependency installer output:\n%s", result.stdout.strip())
        if result.stderr:
            logger.info("Dependency installer diagnostics:\n%s", result.stderr.strip())
        if result.returncode != 0:
            raise RuntimeError(
                "Не удалось установить зависимости. "
                "Проверьте подключение к интернету и файл logs/application.log."
            )

        marker.write_text(requirements_hash, encoding="ascii")
        logger.info("Application dependencies are ready")
    else:
        logging.getLogger("web_constructor.startup").info(
            "Virtual environment and dependencies are up to date"
        )

    current = (current_executable or Path(sys.executable)).resolve()
    should_relaunch = Path(sys.prefix).resolve() != venv_dir.resolve()
    if not gui_interpreter.is_file():
        raise FileNotFoundError(
            f"Не найден интерпретатор виртуального окружения: {gui_interpreter}"
        )
    return gui_interpreter, should_relaunch


def relaunch_in_virtual_environment(interpreter: Path) -> None:
    """Start the application with the project interpreter and exit this process."""
    command = [str(interpreter), str(Path(__file__).resolve())]
    creation_flags = 0
    if os.name == "nt":
        creation_flags = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
    subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        close_fds=True,
        creationflags=creation_flags,
    )


def is_existing_instance(error_code: int) -> bool:
    return error_code == ERROR_ALREADY_EXISTS


def acquire_single_instance() -> tuple[tuple[Any, Any] | None, bool]:
    """Keep a named Windows mutex handle alive while this process is running."""
    if os.name != "nt":
        return None, True

    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_mutex = kernel32.CreateMutexW
    create_mutex.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
    create_mutex.restype = wintypes.HANDLE

    ctypes.set_last_error(0)
    handle = create_mutex(None, False, MUTEX_NAME)
    error_code = ctypes.get_last_error()

    if not handle:
        raise ctypes.WinError(error_code)

    if is_existing_instance(error_code):
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.CloseHandle(handle)
        return None, False

    return (kernel32, handle), True


def show_startup_error(message: str) -> None:
    if os.name != "nt":
        return

    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    message_box = user32.MessageBoxW
    message_box.argtypes = (
        wintypes.HWND,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.UINT,
    )
    message_box.restype = ctypes.c_int
    message_box(None, message, "WEB-Constructor — ошибка запуска", 0x10)


def main() -> None:
    mutex_state: tuple[Any, Any] | None = None
    logger = logging.getLogger("web_constructor.startup")

    try:
        configure_startup_logging()
        logger.info("Application launcher entered")

        interpreter, should_relaunch = prepare_virtual_environment()
        if should_relaunch:
            logger.info("Restarting application with project virtual environment")
            relaunch_in_virtual_environment(interpreter)
            return

        mutex_state, is_first_instance = acquire_single_instance()
        if not is_first_instance:
            logger.info("Another application instance is already running; launch skipped")
            return

        logger.info("Single-instance lock acquired")
        from backend.runtime import run_application

        logger.info("Starting application runtime")
        run_application()

    except Exception:
        logger.exception("Fatal application startup/runtime error")
        show_startup_error(
            "WEB-Constructor не удалось подготовить или запустить.\n\n"
            "Подробности записаны в файл:\n"
            "logs\\application.log"
        )
    finally:
        if mutex_state is not None:
            kernel32, handle = mutex_state
            try:
                from ctypes import wintypes

                kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
                kernel32.CloseHandle.restype = wintypes.BOOL
                kernel32.CloseHandle(handle)
            except Exception:
                logger.exception("Failed to release the single-instance handle")


if __name__ == "__main__":
    main()
