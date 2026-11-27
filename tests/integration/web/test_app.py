from fastapi.testclient import TestClient
from web_helpers import csrf_token

CONTENT_ROUTES = ["/", "/tags", "/tags?view=suggestions", "/filters", "/sources"]


def test_every_content_route_requires_authentication(client: TestClient) -> None:
    for route in CONTENT_ROUTES:
        response = client.get(route, follow_redirects=False)
        assert response.status_code in {302, 303}
        assert response.headers["location"] in {"/login", "/setup"}


def test_first_setup_is_local_and_only_once(client: TestClient) -> None:
    setup = client.get("/setup")
    assert setup.status_code == 200
    assert "Set local password" in setup.text
    response = client.post(
        "/setup",
        data={
            "password": "local-only-password",
            "confirm_password": "local-only-password",
            "csrf_token": csrf_token(setup.text),
        },
        headers={"Origin": "http://127.0.0.1:8765"},
    )
    assert response.status_code in {302, 303}
    assert client.get("/setup", follow_redirects=False).status_code in {302, 303}


def test_wrong_password_does_not_create_a_session(client: TestClient) -> None:
    setup = client.get("/setup")
    client.post(
        "/setup",
        data={
            "password": "local-only-password",
            "confirm_password": "local-only-password",
            "csrf_token": csrf_token(setup.text),
        },
        headers={"Origin": "http://127.0.0.1:8765"},
    )
    login = client.get("/login")
    response = client.post(
        "/login",
        data={
            "password": "wrong-password",
            "csrf_token": csrf_token(login.text),
        },
        headers={"Origin": "http://127.0.0.1:8765"},
    )
    assert response.status_code in {400, 401}
    assert "session" not in client.cookies


def test_feed_search_and_pagination_show_only_saved_posts(client: TestClient) -> None:
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
    response = client.get("/?q=python")
    assert response.status_code == 200
    assert "PYTHON" in response.text
    assert "SQLite" in response.text
    assert "href" in response.text
    assert "page=2" not in response.text


def test_feed_accepts_browser_datetime_local_range(client: TestClient) -> None:
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

    response = client.get(
        "/",
        params={
            "from": "2026-11-09T06:45",
            "to": "2026-11-23T06:45",
            "source": "1001",
        },
    )

    assert response.status_code == 200


def test_bookmark_toggle_changes_the_bookmarked_feed(client: TestClient) -> None:
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
    feed = client.get("/")
    token = csrf_token(feed.text)
    result = client.post(
        "/posts/1001/1/bookmark",
        data={"present": "on", "csrf_token": token},
        headers={"Origin": "http://127.0.0.1:8765"},
    )
    assert result.status_code in {302, 303}
    bookmarked = client.get("/?bookmarked=on")
    assert "Python новости" in bookmarked.text
    assert "Экономика" not in bookmarked.text


def test_tag_and_rule_forms_update_visible_feed(client: TestClient) -> None:
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
    page = client.get("/tags")
    token = csrf_token(page.text)
    tag = client.post(
        "/tags",
        data={"name": "Python", "color": "", "csrf_token": token},
        headers={"Origin": "http://127.0.0.1:8765"},
    )
    assert tag.status_code in {302, 303}
    updated = client.get("/tags")
    assert "Python" in updated.text
    tag_token = csrf_token(updated.text)
    rule = client.post(
        "/tags/1/rules",
        data={"phrase": "python", "csrf_token": tag_token},
        headers={"Origin": "http://127.0.0.1:8765"},
    )
    assert rule.status_code in {302, 303}
    feed = client.get("/?tags=python")
    assert "SQLite" in feed.text
    assert "Экономика" not in feed.text


def test_authenticated_tag_catalogue_exposes_all_mine_and_suggestions_views(
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

    page = client.get("/tags")

    assert page.status_code == 200
    assert "Все теги" in page.text
    assert "Мои теги" in page.text
    assert "Предложения" in page.text


def test_logout_revokes_cookie_and_returns_to_login(client: TestClient) -> None:
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
    logout = client.get("/logout", follow_redirects=False)
    assert logout.status_code in {302, 303}
    assert logout.headers["location"] == "/login"
    assert client.get("/", follow_redirects=False).status_code in {302, 303}
