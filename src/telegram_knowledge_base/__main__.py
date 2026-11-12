import argparse
import sqlite3
import sys

from telegram_knowledge_base.adapters.storage.repository import Repository
from telegram_knowledge_base.adapters.storage.sqlite import initialize_database
from telegram_knowledge_base.config.settings import load_settings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="telegram-knowledge-base")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("login")
    source = commands.add_parser("source")
    source_commands = source.add_subparsers(dest="source_command", required=True)
    add = source_commands.add_parser("add")
    add.add_argument("address")
    source_commands.add_parser("list")
    for action in ("enable", "disable"):
        command = source_commands.add_parser(action)
        command.add_argument("source_id")
    sync = commands.add_parser("sync")
    sync.add_argument("source_id")
    commands.add_parser("status")
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    if arguments.command in {"login", "sync"} or (
        arguments.command == "source" and arguments.source_command == "add"
    ):
        print(
            "Telegram access is disabled until platform requirements are clarified.",
            file=sys.stderr,
        )
        return 2

    try:
        settings = load_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        initialize_database(settings.database_path)
        repository = Repository(settings.database_path)
        if arguments.command == "source":
            if arguments.source_command == "list":
                for source in repository.list_sources():
                    state = "enabled" if source.enabled else "disabled"
                    print(f"{source.telegram_id}\t{state}\t{source.title}")
            else:
                repository.set_enabled(
                    arguments.source_id, arguments.source_command == "enable"
                )
                print("Source updated.")
            return 0
        if arguments.command == "status":
            print(f"Database: {settings.database_path}")
            print(f"Sources: {len(repository.list_sources())}")
            print(f"Posts: {repository.count_posts()}")
            return 0
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
