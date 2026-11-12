import asyncio
import os
import selectors
import socket
import threading
from collections.abc import Coroutine, Iterator
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
