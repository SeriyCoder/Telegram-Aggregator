from telegram_knowledge_base.adapters.auth.passwords import (
    hash_password,
    verify_password,
)
from telegram_knowledge_base.adapters.auth.sessions import (
    generate_session_token,
    session_token_hash,
)
from telegram_knowledge_base.application.ports import AuthStore


def setup_password(store: AuthStore, password: str) -> None:
    if store.has_password_verifier():
        raise ValueError("The local password is already configured.")
    store.save_password_verifier(hash_password(password))


def login(store: AuthStore, password: str) -> str:
    verifier = store.get_password_verifier()
    if verifier is None:
        raise ValueError("Local setup is required.")
    try:
        valid = verify_password(password, verifier)
    except ValueError:
        raise ValueError("Authentication is unavailable.") from None
    if not valid:
        raise ValueError("The password is invalid.")
    token = generate_session_token()
    store.create_session(session_token_hash(token))
    return token


def logout(store: AuthStore, token: str) -> None:
    if not token:
        return
    store.delete_session(session_token_hash(token))


def authenticate(store: AuthStore, token: str | None) -> bool:
    return bool(token) and store.session_exists(session_token_hash(token or ""))
