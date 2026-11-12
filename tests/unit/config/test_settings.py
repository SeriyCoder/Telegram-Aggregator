import logging
from pathlib import Path

import pytest


def test_defaults_use_local_user_data_and_approved_limits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from telegram_knowledge_base.config.settings import load_settings

    local_data = tmp_path / "local-data"
    monkeypatch.setenv("LOCALAPPDATA", str(local_data))
    monkeypatch.setenv("APPDATA", str(local_data))
    monkeypatch.setenv("XDG_DATA_HOME", str(local_data))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    settings = load_settings()

    project_root = Path(__file__).resolve().parents[3]
    assert settings.data_dir.is_absolute()
    assert settings.data_dir.is_relative_to(tmp_path)
    assert not settings.data_dir.is_relative_to(project_root)
    assert settings.database_path.parent == settings.data_dir
    assert settings.collection_limit == 500
    assert settings.page_size == 50


@pytest.mark.parametrize(("collection_limit", "page_size"), [(1, 1), (500, 100)])
def test_local_data_override_and_boundary_limits_are_accepted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    collection_limit: int,
    page_size: int,
) -> None:
    from telegram_knowledge_base.config.settings import load_settings

    data_dir = tmp_path / "data"
    monkeypatch.setenv("TKB_DATA_DIR", str(data_dir))
    monkeypatch.setenv("TKB_COLLECTION_LIMIT", str(collection_limit))
    monkeypatch.setenv("TKB_PAGE_SIZE", str(page_size))

    settings = load_settings()

    assert settings.data_dir == data_dir
    assert settings.database_path.parent == data_dir
    assert settings.collection_limit == collection_limit
    assert settings.page_size == page_size


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("TKB_COLLECTION_LIMIT", "0"),
        ("TKB_COLLECTION_LIMIT", "501"),
        ("TKB_PAGE_SIZE", "0"),
        ("TKB_PAGE_SIZE", "101"),
        ("TKB_PAGE_SIZE", "not-a-number"),
    ],
)
def test_invalid_limits_are_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, value: str
) -> None:
    from telegram_knowledge_base.config.settings import load_settings

    monkeypatch.setenv("TKB_DATA_DIR", str(tmp_path))
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError):
        load_settings()


@pytest.mark.parametrize("value", ["", "relative-data"])
def test_empty_or_relative_data_directory_is_rejected(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    from telegram_knowledge_base.config.settings import load_settings

    monkeypatch.setenv("TKB_DATA_DIR", value)

    with pytest.raises(ValueError):
        load_settings()


def test_repository_data_directory_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    from telegram_knowledge_base.config.settings import load_settings

    project_root = Path(__file__).resolve().parents[3]
    monkeypatch.setenv("TKB_DATA_DIR", str(project_root / "data"))

    with pytest.raises(ValueError):
        load_settings()


def test_configuration_errors_do_not_disclose_environment_secrets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from telegram_knowledge_base.config.settings import load_settings

    secret = "synthetic-telegram-secret"
    monkeypatch.setenv("TKB_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TKB_COLLECTION_LIMIT", "invalid")
    monkeypatch.setenv("TKB_API_HASH", secret)

    with caplog.at_level(logging.ERROR), pytest.raises(ValueError) as error:
        load_settings()

    output = capsys.readouterr()
    assert secret not in str(error.value)
    assert secret not in caplog.text
    assert secret not in output.out
    assert secret not in output.err
