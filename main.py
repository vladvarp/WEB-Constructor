from __future__ import annotations

import ctypes
import logging
import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_FILE = PROJECT_ROOT / "logs" / "application.log"
MUTEX_NAME = "Local\\WEBConstructor.Application"
ERROR_ALREADY_EXISTS = 183


def configure_startup_logging(log_file: Path = LOG_FILE) -> None:
    """Initialize logging before importing any application dependencies."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        encoding="utf-8",
        force=True,
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

    try:
        # Logging must be ready before mutex creation and all third-party imports.
        configure_startup_logging()
        logger = logging.getLogger("web_constructor.startup")
        logger.info("Application launcher entered")

        mutex_state, is_first_instance = acquire_single_instance()
        if not is_first_instance:
            logger.info("Another application instance is already running; launch skipped")
            return

        logger.info("Single-instance lock acquired")
        from backend.runtime import run_application

        logger.info("Starting application runtime")
        run_application()

    except Exception:
        logging.exception("Fatal application startup/runtime error")
        show_startup_error(
            "WEB-Constructor не удалось запустить.\n\n"
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
                logging.exception("Failed to release the single-instance handle")


if __name__ == "__main__":
    main()
