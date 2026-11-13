import logging
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parents[1] / "fixtures" / "exports"


def test_local_entrypoint_initializes_database_without_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from telegram_knowledge_base.__main__ import main
    from telegram_knowledge_base.config.settings import load_settings

    monkeypatch.setenv("TKB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(sys, "argv", ["telegram_knowledge_base"])

    assert main() == 0
    assert load_settings().database_path.is_file()


def test_status_reports_counts_without_printing_post_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from telegram_knowledge_base.__main__ import main
    from telegram_knowledge_base.adapters.storage.repository import Repository
    from telegram_knowledge_base.adapters.storage.sqlite import initialize_database
    from telegram_knowledge_base.domain.models import Post, Progress, Source

    database = tmp_path / "data" / "knowledge.sqlite3"
    monkeypatch.setenv("TKB_DATA_DIR", str(database.parent))
    initialize_database(database)
    repository = Repository(database)
    repository.save_source(Source("123", "public_channel", "Example", True, True))
    repository.commit_batch(
        "123",
        [Post(1, "private post text", "2026-01-01T00:00:00Z")],
        Progress(newest_id=1, oldest_id=1),
    )
    monkeypatch.setattr(sys, "argv", ["telegram_knowledge_base", "status"])

    assert main() == 0
    output = capsys.readouterr().out
    assert "Sources: 1" in output
    assert "Posts: 1" in output
    assert "private post text" not in output


def test_invalid_configuration_reports_failure_without_disclosing_secrets(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from telegram_knowledge_base.__main__ import main

    secret = "synthetic-telegram-secret"
    monkeypatch.setenv("TKB_DATA_DIR", "relative-data")
    monkeypatch.setenv("TKB_API_HASH", secret)
    monkeypatch.setattr(sys, "argv", ["telegram_knowledge_base"])

    with caplog.at_level(logging.ERROR):
        result = main()

    output = capsys.readouterr()
    assert result != 0
    assert output.err or caplog.records
    assert secret not in output.out
    assert secret not in output.err
    assert secret not in caplog.text


@pytest.mark.parametrize(
    "arguments", [["login"], ["source", "add", "@public"], ["sync", "123"]]
)
def test_telegram_commands_fail_closed_without_exposing_secrets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> None:
    from telegram_knowledge_base.__main__ import main

    secret = "synthetic-telegram-secret"
    monkeypatch.setenv("TKB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("TKB_API_HASH", secret)
    monkeypatch.setattr(sys, "argv", ["telegram_knowledge_base", *arguments])

    with caplog.at_level(logging.ERROR):
        result = main()

    output = capsys.readouterr()
    assert result != 0
    assert output.err
    assert secret not in output.out + output.err + caplog.text


def test_import_command_reports_counts_without_printing_post_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from telegram_knowledge_base.__main__ import main

    monkeypatch.setenv("TKB_DATA_DIR", str(tmp_path / "data"))
    export = str(FIXTURES / "public_channel.json")
    monkeypatch.setattr(sys, "argv", ["telegram_knowledge_base", "import", export])

    assert main() == 0
    output = capsys.readouterr().out
    assert "Synthetic Channel" in output
    assert "New: 2" in output
    assert "Existing: 0" in output
    assert "Skipped: 2" in output
    assert "Plain synthetic post" not in output
    assert "Синтетическая часть" not in output


def test_repeated_import_reports_existing_posts_and_adds_nothing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from telegram_knowledge_base.__main__ import main
    from telegram_knowledge_base.adapters.storage.repository import Repository
    from telegram_knowledge_base.config.settings import load_settings

    monkeypatch.setenv("TKB_DATA_DIR", str(tmp_path / "data"))
    export = str(FIXTURES / "public_channel.json")
    monkeypatch.setattr(sys, "argv", ["telegram_knowledge_base", "import", export])
    assert main() == 0
    capsys.readouterr()

    assert main() == 0
    output = capsys.readouterr().out
    assert "New: 0" in output
    assert "Existing: 2" in output
    assert Repository(load_settings().database_path).count_posts() == 2


def test_import_does_not_load_the_telegram_client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from telegram_knowledge_base.__main__ import main

    monkeypatch.setenv("TKB_DATA_DIR", str(tmp_path / "data"))
    export = str(FIXTURES / "public_channel.json")
    monkeypatch.setattr(sys, "argv", ["telegram_knowledge_base", "import", export])
    before = set(sys.modules)

    assert main() == 0
    loaded = set(sys.modules) - before
    assert not any(
        name == "telethon"
        or name.startswith("telethon.")
        or name.startswith("telegram_knowledge_base.adapters.telegram.")
        for name in loaded
    )


@pytest.mark.parametrize(
    "fixture", ["group.json", "personal_chat.json", "full_account.json"]
)
def test_non_channel_exports_are_refused_without_quoting_messages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    fixture: str,
) -> None:
    from telegram_knowledge_base.__main__ import main
    from telegram_knowledge_base.adapters.storage.repository import Repository
    from telegram_knowledge_base.config.settings import load_settings

    monkeypatch.setenv("TKB_DATA_DIR", str(tmp_path / "data"))
    export = str(FIXTURES / fixture)
    monkeypatch.setattr(sys, "argv", ["telegram_knowledge_base", "import", export])

    assert main() == 1
    output = capsys.readouterr()
    assert output.err
    assert "must never be imported" not in output.out + output.err
    assert Repository(load_settings().database_path).count_posts() == 0


def test_corrupted_export_fails_without_changing_the_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from telegram_knowledge_base.__main__ import main
    from telegram_knowledge_base.adapters.storage.repository import Repository
    from telegram_knowledge_base.config.settings import load_settings

    monkeypatch.setenv("TKB_DATA_DIR", str(tmp_path / "data"))
    good = str(FIXTURES / "public_channel.json")
    monkeypatch.setattr(sys, "argv", ["telegram_knowledge_base", "import", good])
    assert main() == 0
    capsys.readouterr()

    bad = str(FIXTURES / "corrupted.json")
    monkeypatch.setattr(sys, "argv", ["telegram_knowledge_base", "import", bad])
    assert main() == 1
    output = capsys.readouterr()
    assert output.err
    assert "Broken Synthetic Channel" not in output.out + output.err
    assert Repository(load_settings().database_path).count_posts() == 2


def test_import_into_disabled_source_is_refused(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from telegram_knowledge_base.__main__ import main
    from telegram_knowledge_base.adapters.storage.repository import Repository
    from telegram_knowledge_base.config.settings import load_settings

    monkeypatch.setenv("TKB_DATA_DIR", str(tmp_path / "data"))
    export = str(FIXTURES / "public_channel.json")
    monkeypatch.setattr(sys, "argv", ["telegram_knowledge_base", "import", export])
    assert main() == 0
    capsys.readouterr()
    monkeypatch.setattr(
        sys, "argv", ["telegram_knowledge_base", "source", "disable", "1234567890"]
    )
    assert main() == 0
    capsys.readouterr()

    monkeypatch.setattr(sys, "argv", ["telegram_knowledge_base", "import", export])
    assert main() == 1
    assert capsys.readouterr().err
    assert Repository(load_settings().database_path).count_posts() == 2
