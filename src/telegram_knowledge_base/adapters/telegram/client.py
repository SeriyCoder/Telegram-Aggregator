from telegram_knowledge_base.domain.models import Post, Source


class TelegramAccessBlocked(Exception):
    pass


class TelegramClient:
    async def login(self) -> None:
        raise TelegramAccessBlocked(
            "Telegram access is disabled until platform requirements are clarified."
        )

    async def resolve(self, address: str) -> Source:
        raise TelegramAccessBlocked(
            "Telegram access is disabled until platform requirements are clarified."
        )

    async def fetch(
        self, source_id: str, *, after: int | None, before: int | None, limit: int
    ) -> list[Post]:
        raise TelegramAccessBlocked(
            "Telegram access is disabled until platform requirements are clarified."
        )
