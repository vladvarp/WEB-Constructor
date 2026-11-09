from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
MODULES_DIR = PROJECT_ROOT / "modules"
LOGS_DIR = PROJECT_ROOT / "logs"
APP_NAME = "WEB-Constructor"
HOST = "127.0.0.1"
STARTUP_TIMEOUT_SECONDS = 12

if os.name == "nt":
    _user_data_root = Path(os.environ.get("LOCALAPPDATA", Path.home()))
else:
    _user_data_root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

DATA_DIR = _user_data_root / "WEB-Constructor"
PROJECTS_DIR = DATA_DIR / "projects"
