from pathlib import Path

from fastapi.testclient import TestClient
from web_helpers import csrf_token


def test_login_and_setup_have_accessible_forms(client: TestClient) -> None:
    for route in ["/login", "/setup"]:
        response = client.get(route)
        assert response.status_code == 200
        assert "<form" in response.text
        assert 'autocomplete="current-password"' in response.text or (
            'autocomplete="new-password"' in response.text
        )
        assert 'name="csrf_token"' in response.text
        assert 'lang="ru"' in response.text


def test_authenticated_shell_has_mobile_viewport_skip_link_and_local_assets(
    client: TestClient,
) -> None:
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
    assert 'name="viewport"' in response.text
    assert 'class="skip-link"' in response.text
    assert "/static/app.css" in response.text
    assert "http://" not in response.text.replace("http://127.0.0.1:8765", "")
    assert "https://" not in response.text


def test_core_pages_exist_after_login(client: TestClient) -> None:
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
    for route in ["/", "/tags", "/filters", "/sources"]:
        response = client.get(route)
        assert response.status_code == 200
        assert "<main" in response.text


def test_css_has_mobile_layout_and_launcher_targets_loopback() -> None:
    root = Path(__file__).resolve().parents[3]
    css = (
        root / "src" / "telegram_knowledge_base" / "web" / "static" / "app.css"
    ).read_text(encoding="utf-8")
    launcher = (root / "scripts" / "start_gui.ps1").read_text(encoding="utf-8")

    assert "@media" in css
    assert "min-width: 0" in css
    assert "overflow-wrap" in css
    assert "127.0.0.1" in launcher
    assert "8765" in launcher
    assert "0.0.0.0" not in launcher
    assert "Start-Process" in launcher
