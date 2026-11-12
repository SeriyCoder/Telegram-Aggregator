import logging
import traceback

import pytest
from conftest import run_offline

from telegram_knowledge_base.application.ports import SourceAccessError
from telegram_knowledge_base.application.sources import add_source
from telegram_knowledge_base.domain.models import Source


class Resolver:
    def __init__(self, source: Source) -> None:
        self.source = source

    async def resolve(self, address: str) -> Source:
        return self.source


class Store:
    def __init__(self) -> None:
        self.sources: list[Source] = []

    def save_source(self, source: Source) -> None:
        self.sources.append(source)


def test_manually_selected_public_channel_is_added() -> None:
    source = Source("123", "public_channel", "Example", True, True)
    store = Store()

    run_offline(add_source(store, Resolver(source), "@public_channel"))

    assert store.sources == [source]


@pytest.mark.parametrize(
    "source",
    [
        Source("1", None, "Private", True, False),
        Source("2", "public_group", "Group", False, True),
    ],
)
def test_private_channels_and_groups_are_rejected(source: Source) -> None:
    store = Store()

    with pytest.raises(ValueError):
        run_offline(add_source(store, Resolver(source), "@looks_public"))

    assert store.sources == []


def test_invitation_links_are_rejected_without_resolving() -> None:
    class NoResolve:
        async def resolve(self, address: str) -> Source:
            raise AssertionError("Invitation link must not be resolved")

    store = Store()
    with pytest.raises(ValueError):
        run_offline(add_source(store, NoResolve(), "https://t.me/+example"))
    assert store.sources == []


def test_resolver_cannot_substitute_a_different_public_channel() -> None:
    source = Source("456", "different_channel", "Other", True, True)
    store = Store()

    with pytest.raises(ValueError):
        run_offline(add_source(store, Resolver(source), "@public_channel"))

    assert store.sources == []


def test_source_access_failure_does_not_expose_secrets(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "synthetic-source-access-key"

    class FailedResolver:
        async def resolve(self, address: str) -> Source:
            raise RuntimeError(f"upstream failure: {secret}")

    store = Store()
    with caplog.at_level(logging.ERROR), pytest.raises(SourceAccessError) as error:
        run_offline(add_source(store, FailedResolver(), "@public_channel"))
    assert secret not in "".join(traceback.format_exception(error.value))
    assert secret not in caplog.text
    assert store.sources == []
