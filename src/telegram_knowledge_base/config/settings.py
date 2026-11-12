import ctypes
import os
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from platformdirs import user_data_path


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    database_path: Path
    collection_limit: int
    page_size: int


def load_settings() -> Settings:
    data_dir = _data_directory()
    collection_limit = _integer_setting("TKB_COLLECTION_LIMIT", 500, 500)
    page_size = _integer_setting("TKB_PAGE_SIZE", 50, 100)

    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "knowledge.sqlite3",
        collection_limit=collection_limit,
        page_size=page_size,
    )


def _data_directory() -> Path:
    configured = os.environ.get("TKB_DATA_DIR")
    if configured is None:
        candidate = user_data_path("Telegram Knowledge Base", appauthor=False)
    else:
        if not configured.strip():
            raise ValueError("TKB_DATA_DIR must be a non-empty absolute path.")
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise ValueError("TKB_DATA_DIR must be a non-empty absolute path.")

    if _is_network_path(candidate) or _is_cloud_sync_path(candidate):
        raise ValueError(
            "TKB_DATA_DIR must be a local directory outside cloud-synced storage."
        )

    data_dir = candidate.resolve()
    if _is_network_path(data_dir) or _is_cloud_sync_path(data_dir):
        raise ValueError(
            "TKB_DATA_DIR must be a local directory outside cloud-synced storage."
        )
    project_root = _project_root()
    if project_root is not None and data_dir.is_relative_to(project_root):
        raise ValueError("TKB_DATA_DIR must be outside the project directory.")
    return data_dir


def _is_network_path(path: Path) -> bool:
    windows_path = PureWindowsPath(str(path))
    if windows_path.drive.startswith("\\\\"):
        return True
    if os.name == "nt" and windows_path.drive:
        drive_root = f"{windows_path.drive}\\"
        return int(ctypes.windll.kernel32.GetDriveTypeW(drive_root)) == 4
    return False


def _is_cloud_sync_path(path: Path) -> bool:
    resolved = path.resolve()
    for name in (
        "OneDrive",
        "OneDriveCommercial",
        "OneDriveConsumer",
        "Dropbox",
        "GoogleDrive",
        "GDRIVE",
    ):
        root = os.environ.get(name)
        if root:
            sync_root = Path(root).expanduser().resolve()
            if resolved.is_relative_to(sync_root):
                return True
    return False


def _integer_setting(name: str, default: int, maximum: int) -> int:
    configured = os.environ.get(name)
    if configured is None:
        return default

    try:
        value = int(configured)
    except ValueError:
        raise ValueError(
            f"{name} must be an integer between 1 and {maximum}."
        ) from None

    if not 1 <= value <= maximum:
        raise ValueError(f"{name} must be an integer between 1 and {maximum}.")
    return value


def _project_root() -> Path | None:
    module_path = Path(__file__).resolve()
    for parent in module_path.parents:
        if (parent / "pyproject.toml").is_file() and (
            parent / "src" / "telegram_knowledge_base"
        ).is_dir():
            return parent
    return None
