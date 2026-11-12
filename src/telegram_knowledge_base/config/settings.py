import os
from dataclasses import dataclass
from pathlib import Path

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

    data_dir = candidate.resolve()
    project_root = _project_root()
    if project_root is not None and data_dir.is_relative_to(project_root):
        raise ValueError("TKB_DATA_DIR must be outside the project directory.")
    return data_dir


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
