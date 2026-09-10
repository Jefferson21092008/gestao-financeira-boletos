import ctypes
import os
from pathlib import Path

from config import APP_FOLDER, DB_NAME


def get_app_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".local" / "share"
    app_dir = base / APP_FOLDER
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


DB_PATH = get_app_data_dir() / DB_NAME
BACKUP_DIR = get_app_data_dir() / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def escape_ps(value: str) -> str:
    return value.replace("'", "''")


def get_windows_desktop_path() -> Path:
    buf = ctypes.create_unicode_buffer(260)
    CSIDL_DESKTOPDIRECTORY = 0x10
    result = ctypes.windll.shell32.SHGetFolderPathW(
        None, CSIDL_DESKTOPDIRECTORY, None, 0, buf
    )
    if result != 0:
        return Path.home() / "Desktop"
    return Path(buf.value)


def get_entrypoint_path() -> Path:
    """Retorna o main.py da aplicação modular."""
    return Path(__file__).resolve().parents[1] / "main.py"
