from __future__ import annotations

import logging
import socket
import threading
import time
import urllib.error
import urllib.request

import uvicorn
import webview

from backend.app import app
from backend.core.config import APP_NAME, HOST, LOGS_DIR, STARTUP_TIMEOUT_SECONDS


def configure_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=LOGS_DIR / "application.log", level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                        encoding="utf-8")


def find_available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def wait_for_backend(port: int, timeout: float) -> None:
    url = f"http://{HOST}:{port}/api/health"
    deadline, last_error = time.monotonic() + timeout, None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
        time.sleep(0.1)
    raise RuntimeError(f"Backend startup timed out: {last_error}")


def run_application() -> None:
    configure_logging()
    logger = logging.getLogger("web_constructor.runtime")
    server = server_thread = None
    try:
        port = find_available_port()
        server = uvicorn.Server(uvicorn.Config(
            app, host=HOST, port=port, log_level="warning",
            access_log=False, lifespan="off"
        ))
        server_thread = threading.Thread(target=server.run,
                                         name="web-constructor-api", daemon=True)
        server_thread.start()
        wait_for_backend(port, STARTUP_TIMEOUT_SECONDS)
        webview.create_window(APP_NAME, f"http://{HOST}:{port}/",
                              width=1440, height=900, min_size=(1000, 650))
        webview.start(debug=False)
    except Exception:
        logger.exception("Application startup or runtime failed")
        raise
    finally:
        if server is not None:
            server.should_exit = True
        if server_thread is not None and server_thread.is_alive():
            server_thread.join(timeout=5)
