import os
import socket
from collections.abc import Iterator
from typing import NoReturn

import pytest


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

    for name in ("connect", "connect_ex", "bind", "listen", "send", "sendall", "sendto"):
        monkeypatch.setattr(socket.socket, name, reject_network)
    for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"):
        monkeypatch.setattr(socket, name, reject_network)

    yield

    assert not attempts, "The application attempted a network operation"
