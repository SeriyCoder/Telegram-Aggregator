import sqlite3
import sys

from telegram_knowledge_base.adapters.storage.sqlite import initialize_database
from telegram_knowledge_base.config.settings import load_settings


def main() -> int:
    try:
        settings = load_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        initialize_database(settings.database_path)
    except (OSError, sqlite3.Error, ValueError):
        print(
            "Local database initialization failed. Check the configuration "
            "and data directory.",
            file=sys.stderr,
        )
        return 1

    print("Local database initialized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
