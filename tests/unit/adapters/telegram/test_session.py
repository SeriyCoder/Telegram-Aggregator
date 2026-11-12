import logging
import traceback
from pathlib import Path

import pytest

from telegram_knowledge_base.adapters.telegram.session import (
    SessionStorageError,
    SessionStore,
)


class Backend:
    def __init__(self, secure: bool, *, fail: bool = False) -> None:
        self.secure = secure
        self.fail = fail
        self.value: str | None = None

    def set_secret(self, value: str) -> None:
        if self.fail:
            raise OSError(f"backend failure: {value}")
        self.value = value

    def get_secret(self) -> str | None:
        return self.value


def test_session_uses_secure_backend_without_plaintext_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    backend = Backend(True)
    store = SessionStore(backend)
    secret = "synthetic-session-key"

    store.save(secret)

    assert store.load() == secret
    assert list(tmp_path.iterdir()) == []


def test_insecure_backend_is_rejected_without_fallback() -> None:
    backend = Backend(False)
    with pytest.raises(SessionStorageError):
        SessionStore(backend).save("synthetic-session-key")
    assert backend.value is None


def test_backend_errors_never_expose_session_material(
    caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = "synthetic-session-key"
    with caplog.at_level(logging.ERROR), pytest.raises(SessionStorageError) as error:
        SessionStore(Backend(True, fail=True)).save(secret)
    output = capsys.readouterr()
    assert secret not in str(error.value)
    assert secret not in "".join(traceback.format_exception(error.value))
    assert secret not in caplog.text
    assert secret not in output.out + output.err
