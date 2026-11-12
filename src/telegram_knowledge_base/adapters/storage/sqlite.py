import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA_VERSION = 2
_MIGRATIONS = {
    1: Path(__file__).with_name("migrations") / "0001_initial.sql",
    2: Path(__file__).with_name("migrations") / "0002_sync.sql",
}


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

        migrations = [
            path.read_text(encoding="utf-8")
            for number, path in _MIGRATIONS.items()
            if number > version
        ]
        if not migrations:
            raise sqlite3.DatabaseError("No migration is available for this schema.")
        script = "\n".join(migrations)
        connection.executescript(
            "BEGIN IMMEDIATE;\n"
            f"{script}\n"
            f"PRAGMA user_version = {SCHEMA_VERSION};\n"
            "COMMIT;"
        )
