import asyncio
from urllib.parse import urlsplit

from telegram_knowledge_base.application.ports import (
    SourceAccessError,
    SourceResolver,
    SourceStore,
)


def _username(address: str) -> str:
    value = address.strip()
    if value.startswith("@"):
        username = value[1:]
    else:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"https", "http"}
            or parsed.netloc.lower() not in {"t.me", "telegram.me", "www.t.me"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Select a public Telegram channel by username.")
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 1:
            raise ValueError("Invitation links and non-channel paths are unsupported.")
        username = parts[0]

    if (
        not 5 <= len(username) <= 32
        or not username.isascii()
        or not all(char.isalnum() or char == "_" for char in username)
    ):
        raise ValueError("Select a public Telegram channel by username.")
    return username


async def add_source(
    store: SourceStore, resolver: SourceResolver, address: str
) -> None:
    username = _username(address)
    try:
        source = await resolver.resolve(username)
    except Exception:
        raise SourceAccessError(
            "The selected Telegram source could not be resolved."
        ) from None

    if (
        not source.is_channel
        or not source.is_public
        or source.username is None
        or source.username.casefold() != username.casefold()
    ):
        raise ValueError("Only public Telegram channels can be added.")
    await asyncio.to_thread(store.save_source, source)
