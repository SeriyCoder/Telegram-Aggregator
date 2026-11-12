import logging
import sys
from pathlib import Path

import pytest


def test_local_entrypoint_initializes_database_without_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from telegram_knowledge_base.__main__ import main
    from telegram_knowledge_base.config.settings import load_settings

    monkeypatch.setenv("TKB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(sys, "argv", ["telegram_knowledge_base"])

    assert main() == 0
    assert load_settings().database_path.is_file()


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
