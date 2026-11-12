import pytest
from conftest import run_offline

from telegram_knowledge_base.adapters.telegram.client import (
    TelegramAccessBlocked,
    TelegramClient,
)


@pytest.mark.parametrize("operation", ["login", "resolve", "fetch"])
def test_real_telegram_operations_are_blocked(operation: str) -> None:
    client = TelegramClient()
    if operation == "login":
        call = client.login()
    elif operation == "resolve":
        call = client.resolve("@example")
    else:
        call = client.fetch("123", after=None, before=None, limit=1)

    with pytest.raises(TelegramAccessBlocked):
        run_offline(call)
