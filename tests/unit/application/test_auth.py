import pytest

from telegram_knowledge_base.application.auth import (
    authenticate,
    login,
    logout,
    setup_password,
)


class Store:
    def __init__(self) -> None:
        self.verifier: str | None = None
        self.sessions: set[str] = set()

    def has_password_verifier(self) -> bool:
        return self.verifier is not None

    def save_password_verifier(self, verifier: str) -> None:
        if self.verifier is not None:
            raise ValueError("The local password is already configured.")
        self.verifier = verifier

    def get_password_verifier(self) -> str | None:
        return self.verifier

    def create_session(self, token_hash: str) -> None:
        self.sessions.add(token_hash)

    def delete_session(self, token_hash: str) -> None:
        self.sessions.discard(token_hash)

    def session_exists(self, token_hash: str) -> bool:
        return token_hash in self.sessions


def test_first_setup_creates_verifier_but_never_stores_password() -> None:
    store = Store()
    password = "local-only-password"

    setup_password(store, password)

    assert store.verifier is not None
    assert password not in store.verifier
    assert store.sessions == set()


def test_setup_is_allowed_only_once() -> None:
    store = Store()
    setup_password(store, "local-only-password")

    with pytest.raises(ValueError):
        setup_password(store, "different-local-password")


def test_login_requires_the_configured_password_and_returns_random_token() -> None:
    store = Store()
    setup_password(store, "local-only-password")

    first = login(store, "local-only-password")
    second = login(store, "local-only-password")

    assert first != second
    assert authenticate(store, first) is True
    assert authenticate(store, second) is True
    with pytest.raises(ValueError):
        login(store, "wrong-password")


def test_logout_revokes_only_the_selected_opaque_session() -> None:
    store = Store()
    setup_password(store, "local-only-password")
    token = login(store, "local-only-password")
    other = login(store, "local-only-password")

    logout(store, token)

    assert authenticate(store, token) is False
    assert authenticate(store, other) is True


@pytest.mark.parametrize("token", [None, "", "forged-token"])
def test_missing_or_forged_session_is_unauthenticated(token: str | None) -> None:
    store = Store()
    assert authenticate(store, token) is False
