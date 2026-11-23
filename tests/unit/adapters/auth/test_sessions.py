from telegram_knowledge_base.adapters.auth.sessions import (
    generate_session_token,
    session_token_hash,
)


def test_session_tokens_are_random_and_only_the_hash_is_stored_shape() -> None:
    first = generate_session_token()
    second = generate_session_token()

    assert first != second
    assert len(first) >= 43
    assert session_token_hash(first) != first
    assert session_token_hash(first) == session_token_hash(first)
    assert session_token_hash(first) != session_token_hash(second)
