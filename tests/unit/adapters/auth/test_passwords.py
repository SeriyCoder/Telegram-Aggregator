import pytest

from telegram_knowledge_base.adapters.auth.passwords import (
    hash_password,
    verify_password,
)


def test_password_verifier_is_salted_and_constant_shape() -> None:
    first = hash_password("synthetic password")
    second = hash_password("synthetic password")

    assert first != second
    assert "synthetic password" not in first
    assert verify_password("synthetic password", first) is True
    assert verify_password("wrong password", first) is False


@pytest.mark.parametrize("password", ["", " ", "short"])
def test_weak_or_empty_password_is_rejected(password: str) -> None:
    with pytest.raises(ValueError):
        hash_password(password)


def test_invalid_password_verifier_fails_closed_without_exposing_it() -> None:
    secret = "synthetic-verifier-secret"

    with pytest.raises(ValueError) as error:
        verify_password("synthetic password", secret)

    assert secret not in str(error.value)
