from fastapi import Request

from telegram_knowledge_base.adapters.storage.repository import Repository
from telegram_knowledge_base.application.auth import authenticate


def repository(request: Request) -> Repository:
    value = getattr(request.app.state, "repository", None)
    if not isinstance(value, Repository):
        raise RuntimeError("The repository is unavailable.")
    return value


def authenticated(request: Request) -> Repository:
    store = repository(request)
    if not authenticate(store, request.cookies.get("session")):
        raise AuthenticationRequired
    return store


class AuthenticationRequired(Exception):
    pass
