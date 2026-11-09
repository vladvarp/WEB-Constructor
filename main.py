from __future__ import annotations

import logging
import os
from pathlib import Path
import traceback

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_FILE = PROJECT_ROOT / "logs" / "application.log"


def acquire_single_instance():
    """Keep a Windows named mutex alive for the lifetime of this process."""
    if os.name != "nt":
        return None, True

    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.ReleaseMutex.argtypes = [ctypes.c_void_p]
    ctypes.set_last_error(0)
    mutex = kernel32.CreateMutexW(None, True, "Local\\WEBConstructor.Application")
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())

    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(mutex)
        return None, False

    return (kernel32, mutex), True


def show_startup_error(message: str) -> None:
    if os.name == "nt":
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None,
            message,
            "WEB-Constructor — ошибка запуска",
            0x10 | 0x0,
        )


def main() -> None:
    mutex_state = None
    try:
        mutex_state, is_first_instance = acquire_single_instance()
        if not is_first_instance:
            return

        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            encoding="utf-8",
            force=True,
        )
        logging.info("Application entry point reached")

        from backend.runtime import run_application
        run_application()

    except Exception:
        details = traceback.format_exc()
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with LOG_FILE.open("a", encoding="utf-8") as log:
                log.write("\n--- FATAL APPLICATION ERROR ---\n")
                log.write(details)
        except OSError:
            pass

        show_startup_error(
            "WEB-Constructor не удалось запустить.\n\n"
            "Подробности записаны в logs\\application.log.\n\n"
            + details[-1800:]
        )
    finally:
        if mutex_state is not None:
            kernel32, mutex = mutex_state
            kernel32.ReleaseMutex(mutex)
            kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
