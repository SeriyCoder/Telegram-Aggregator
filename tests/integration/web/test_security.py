from pathlib import Path

from fastapi.testclient import TestClient
from web_helpers import csrf_token


def test_content_routes_do_not_serve_database_or_source_paths(
    client: TestClient,
) -> None:
    for path in (
        "/knowledge.sqlite3",
        "/../pyproject.toml",
        "/static/../result.json",
        "/%2e%2e/%2e%2e/pyproject.toml",
    ):
        response = client.get(path)
        assert response.status_code in {401, 403, 404}
        assert "Telegram Knowledge Base" not in response.text
        assert "OneDrive" not in response.text


def test_login_setup_and_errors_do_not_echo_sentinel_secrets(
    client: TestClient,
) -> None:
    secret = "synthetic-private-password"
    setup = client.get("/setup")
    response = client.post(
        "/setup",
        data={
            "password": secret,
            "confirm_password": "mismatch",
            "csrf_token": csrf_token(setup.text),
        },
        headers={"Origin": "http://127.0.0.1:8765"},
    )
    rendered = response.text + "\n".join(response.headers.values())
    assert secret not in rendered


def test_post_mutation_requires_csrf_and_exact_loopback_origin(
    client: TestClient,
) -> None:
    setup = client.get("/setup")
    token = csrf_token(setup.text)
    client.post(
        "/setup",
        data={
            "password": "local-only-password",
            "confirm_password": "local-only-password",
            "csrf_token": token,
        },
        headers={"Origin": "http://127.0.0.1:8765"},
        follow_redirects=True,
    )
    for headers, form_token in [
        ({"Origin": "http://127.0.0.1:8765"}, None),
        ({"Origin": "https://evil.invalid"}, token),
    ]:
        data = {"name": "Injected", "color": ""}
        if form_token is not None:
            data["csrf_token"] = form_token
        response = client.post("/tags", data=data, headers=headers)
        assert response.status_code in {400, 403}


def test_tampered_session_cookie_cannot_access_content(client: TestClient) -> None:
    setup = client.get("/setup")
    client.post(
        "/setup",
        data={
            "password": "local-only-password",
            "confirm_password": "local-only-password",
            "csrf_token": csrf_token(setup.text),
        },
        headers={"Origin": "http://127.0.0.1:8765"},
        follow_redirects=True,
    )
    client.cookies.set("session", "forged-token")
    assert client.get("/", follow_redirects=False).status_code in {302, 303}


def test_html_escapes_post_text_and_has_basic_security_headers(
    client: TestClient,
    web_database: Path,
) -> None:
    from telegram_knowledge_base.adapters.storage.repository import Repository
    from telegram_knowledge_base.domain.models import Post, Source

    Repository(web_database).save_import(
        Source("1003", None, "Synthetic XSS", True, True),
        [Post(1, "<script>alert('private')</script>", "2026-01-04T00:00:00Z")],
    )
    setup = client.get("/setup")
    client.post(
        "/setup",
        data={
            "password": "local-only-password",
            "confirm_password": "local-only-password",
            "csrf_token": csrf_token(setup.text),
        },
        headers={"Origin": "http://127.0.0.1:8765"},
        follow_redirects=True,
    )
    response = client.get("/")
    assert "&lt;script&gt;" in response.text
    assert "<script>alert('private')</script>" not in response.text
    assert response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_routes_do_not_load_telegram_client(client: TestClient) -> None:
    import sys

    before = set(sys.modules)
    for route in ["/health", "/setup", "/login"]:
        client.get(route)
    loaded = set(sys.modules) - before
    assert not any(
        name == "telethon"
        or name.startswith("telethon.")
        or name.startswith("telegram_knowledge_base.adapters.telegram.")
        for name in loaded
    )
