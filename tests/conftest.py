import asyncio
import json
import os
import selectors
import socket
import threading
from collections.abc import Coroutine, Iterator
from pathlib import Path
from typing import Any, NoReturn

import pytest


class OfflineSelector(selectors.SelectSelector):
    def __init__(self) -> None:
        super().__init__()
        self.ready = threading.Event()

    def register(
        self, fileobj: Any, events: int, data: Any = None
    ) -> selectors.SelectorKey:
        raise AssertionError("I/O registration is forbidden in offline tests")

    def select(
        self, timeout: float | None = None
    ) -> list[tuple[selectors.SelectorKey, int]]:
        wait = 5.0 if timeout is None else timeout
        signaled = self.ready.wait(wait)
        self.ready.clear()
        if timeout is None and not signaled:
            raise AssertionError("Offline event loop stalled")
        return []


class OfflineEventLoop(asyncio.SelectorEventLoop):
    def __init__(self) -> None:
        self.offline_selector = OfflineSelector()
        super().__init__(selector=self.offline_selector)

    def _make_self_pipe(self) -> None:
        pass

    def _close_self_pipe(self) -> None:
        pass

    def _write_to_self(self) -> None:
        self.offline_selector.ready.set()


def run_offline[T](coroutine: Coroutine[Any, Any, T]) -> T:
    with asyncio.Runner(loop_factory=OfflineEventLoop) as runner:
        return runner.run(coroutine)


@pytest.fixture(autouse=True)
def isolate_project_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in tuple(os.environ):
        if name.startswith("TKB_"):
            monkeypatch.delenv(name)


@pytest.fixture(autouse=True)
def prevent_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    attempts: list[str] = []

    def reject_network(*args: object, **kwargs: object) -> NoReturn:
        attempts.append("network operation")
        raise AssertionError("Network operations are forbidden in tests")

    for name in (
        "connect",
        "connect_ex",
        "bind",
        "listen",
        "send",
        "sendall",
        "sendto",
    ):
        monkeypatch.setattr(socket.socket, name, reject_network)
    for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"):
        monkeypatch.setattr(socket, name, reject_network)

    yield

    assert not attempts, "The application attempted a network operation"


@pytest.fixture
def web_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    from telegram_knowledge_base.adapters.storage.repository import Repository
    from telegram_knowledge_base.adapters.storage.sqlite import initialize_database
    from telegram_knowledge_base.domain.models import Post, Source

    data_dir = tmp_path / "data"
    monkeypatch.setenv("TKB_DATA_DIR", str(data_dir))
    database = data_dir / "knowledge.sqlite3"
    initialize_database(database)
    repository = Repository(database)
    fixture = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "knowledge"
        / "russian_posts.json"
    )
    document = json.loads(fixture.read_text(encoding="utf-8"))
    for item in document["sources"]:
        source = Source(
            item["telegram_id"],
            None,
            item["title"],
            item["is_channel"],
            item["is_public"],
        )
        repository.save_import(
            source,
            [
                Post(post["message_id"], post["text"], post["published_at"])
                for post in item["posts"]
            ],
        )
    yield database


@pytest.fixture
def client(web_database: Path) -> Iterator[Any]:
    from fastapi.testclient import TestClient

    from telegram_knowledge_base.web.app import create_app

    with TestClient(
        create_app(),
        base_url="http://127.0.0.1:8765",
        backend_options={"loop_factory": OfflineEventLoop},
        follow_redirects=False,
    ) as test_client:
        yield test_client
