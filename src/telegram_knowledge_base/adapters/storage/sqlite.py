import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA_VERSION = 1
_MIGRATION_FILE = Path(__file__).with_name("migrations") / "0001_initial.sql"


def initialize_database(database: Path) -> None:
    database.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        version_row = connection.execute("PRAGMA user_version").fetchone()
        if version_row is None:
            raise sqlite3.DatabaseError("Could not read the database schema version.")

        version = version_row[0]
        if version > SCHEMA_VERSION:
            raise ValueError(
                "The database schema is newer than this application supports."
            )
        if version == SCHEMA_VERSION:
            return

        migration = _MIGRATION_FILE.read_text(encoding="utf-8")
        connection.executescript(
            "BEGIN IMMEDIATE;\n"
            f"{migration}\n"
            f"PRAGMA user_version = {SCHEMA_VERSION};\n"
            "COMMIT;"
        )
