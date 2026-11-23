"""Local web adapter. FastAPI dependencies intentionally use call defaults."""
# ruff: noqa: B008

import secrets
from pathlib import Path
from typing import Any, cast

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from telegram_knowledge_base.adapters.storage.repository import Repository
from telegram_knowledge_base.adapters.storage.sqlite import initialize_database
from telegram_knowledge_base.application.auth import (
    login,
    logout,
    setup_password,
)
from telegram_knowledge_base.application.knowledge import (
    create_filter_rule,
    create_tag,
    create_tag_rule,
    delete_filter_rule,
    delete_tag,
    delete_tag_rule,
    query_posts,
    set_bookmark,
    set_filter_rule_enabled,
    set_manual_tag,
    set_tag_rule_enabled,
)
from telegram_knowledge_base.config.settings import Settings, load_settings
from telegram_knowledge_base.web.dependencies import (
    AuthenticationRequired,
    authenticated,
    repository,
)
from telegram_knowledge_base.web.forms import (
    parse_post_query,
    validate_csrf,
    validate_origin,
)

_SESSION_COOKIE = "session"
_CSRF_COOKIE = "csrf"
_SESSION_SECONDS = 12 * 60 * 60
_PACKAGE = Path(__file__).resolve().parent
_EXPECTED_ORIGIN = "http://127.0.0.1:8765"


def create_app(settings: Settings | None = None) -> FastAPI:
    current = settings or load_settings()
    initialize_database(current.database_path)
    app = FastAPI(title="Telegram Knowledge Base", docs_url=None, redoc_url=None)
    app.state.repository = Repository(current.database_path)
    app.state.settings = current
    templates = Jinja2Templates(directory=str(_PACKAGE / "templates"))
    app.mount(
        "/static",
        StaticFiles(directory=str(_PACKAGE / "static")),
        name="static",
    )

    @app.exception_handler(AuthenticationRequired)
    async def require_authentication(
        request: Request, error: AuthenticationRequired
    ) -> Response:
        del error
        store = repository(request)
        target = "/login" if store.has_password_verifier() else "/setup"
        return RedirectResponse(target, status_code=303)

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Response:
        response = cast(Response, await call_next(request))
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
            "form-action 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/setup", response_class=HTMLResponse)
    def setup_get(
        request: Request, store: Repository = Depends(repository)
    ) -> Response:
        if store.has_password_verifier():
            target = "/" if authenticated_or_false(store, request) else "/login"
            return RedirectResponse(target, status_code=303)
        csrf = ensure_csrf_cookie(request)
        response = templates.TemplateResponse(
            request,
            "setup.html",
            {"request": request, "csrf_token": csrf, "error": None},
        )
        response.set_cookie(_CSRF_COOKIE, csrf, httponly=True, samesite="strict")
        return response

    @app.post("/setup", response_class=HTMLResponse)
    def setup_post(
        request: Request,
        password: str = Form(),
        confirm_password: str = Form(),
        csrf_token: str | None = Form(None),
        store: Repository = Depends(repository),
    ) -> Response:
        try:
            secure_form(request, csrf_token)
            if password != confirm_password:
                raise ValueError("The password confirmation does not match.")
            setup_password(store, password)
            return login_response(store, password)
        except ValueError:
            csrf = ensure_csrf_cookie(request)
            response = templates.TemplateResponse(
                request,
                "setup.html",
                {
                    "request": request,
                    "csrf_token": csrf,
                    "error": "Unable to complete local setup.",
                },
                status_code=400,
            )
            response.set_cookie(_CSRF_COOKIE, csrf, httponly=True, samesite="strict")
            return response

    @app.get("/login", response_class=HTMLResponse)
    def login_get(
        request: Request, store: Repository = Depends(repository)
    ) -> Response:
        del store
        csrf = ensure_csrf_cookie(request)
        response = templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "csrf_token": csrf, "error": None},
        )
        response.set_cookie(_CSRF_COOKIE, csrf, httponly=True, samesite="strict")
        return response

    @app.post("/login", response_class=HTMLResponse)
    def login_post(
        request: Request,
        password: str = Form(),
        csrf_token: str | None = Form(None),
        store: Repository = Depends(repository),
    ) -> Response:
        try:
            secure_form(request, csrf_token)
            return login_response(store, password)
        except ValueError:
            logout(store, request.cookies.get(_SESSION_COOKIE) or "")
            csrf = ensure_csrf_cookie(request)
            response = templates.TemplateResponse(
                request,
                "login.html",
                {"request": request, "csrf_token": csrf, "error": "Unable to sign in."},
                status_code=401,
            )
            response.set_cookie(_CSRF_COOKIE, csrf, httponly=True, samesite="strict")
            response.delete_cookie(_SESSION_COOKIE)
            return response

    @app.get("/logout")
    def logout_get(
        request: Request, store: Repository = Depends(repository)
    ) -> Response:
        logout(store, request.cookies.get(_SESSION_COOKIE) or "")
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(_SESSION_COOKIE)
        return response

    @app.get("/", response_class=HTMLResponse)
    def feed(
        request: Request,
        store: Repository = Depends(authenticated),
    ) -> Response:
        query = parse_post_query(
            {key: value for key, value in request.query_params.multi_items()}
        )
        page = query_posts(store, query)
        return content_response(
            request,
            templates,
            "feed.html",
            {
                "page": page,
                "tags": store.list_tags(),
                "sources": store.list_sources(),
                "filters": request.query_params,
            },
        )

    @app.post("/posts/{source_id}/{message_id}/bookmark")
    def bookmark_post(
        source_id: str,
        message_id: int,
        request: Request,
        present: str | None = Form(None),
        csrf_token: str | None = Form(None),
        store: Repository = Depends(authenticated),
    ) -> Response:
        secure_form(request, csrf_token)
        set_bookmark(store, source_id, message_id, present == "on")
        return RedirectResponse("/", status_code=303)

    @app.post("/posts/{source_id}/{message_id}/tag")
    def manual_tag_post(
        source_id: str,
        message_id: int,
        request: Request,
        tag_id: int = Form(),
        present: str | None = Form(None),
        csrf_token: str | None = Form(None),
        store: Repository = Depends(authenticated),
    ) -> Response:
        secure_form(request, csrf_token)
        set_manual_tag(store, source_id, message_id, tag_id, present == "on")
        return RedirectResponse("/", status_code=303)

    @app.get("/tags", response_class=HTMLResponse)
    def tags_get(
        request: Request, store: Repository = Depends(authenticated)
    ) -> Response:
        tags = store.list_tags()
        rules = {tag.id: store.list_tag_rules(tag.id) for tag in tags}
        return content_response(
            request, templates, "tags.html", {"tags": tags, "rules": rules}
        )

    @app.post("/tags")
    def tag_create(
        request: Request,
        name: str = Form(),
        color: str = Form(""),
        csrf_token: str | None = Form(None),
        store: Repository = Depends(authenticated),
    ) -> Response:
        secure_form(request, csrf_token)
        create_tag(store, name, color or None)
        return RedirectResponse("/tags", status_code=303)

    @app.post("/tags/{tag_id}/rules")
    def tag_rule_create(
        tag_id: int,
        request: Request,
        phrase: str = Form(),
        csrf_token: str | None = Form(None),
        store: Repository = Depends(authenticated),
    ) -> Response:
        secure_form(request, csrf_token)
        create_tag_rule(store, tag_id, phrase)
        return RedirectResponse("/tags", status_code=303)

    @app.post("/tag-rules/{rule_id}/toggle")
    def tag_rule_toggle(
        rule_id: int,
        request: Request,
        enabled: str | None = Form(None),
        csrf_token: str | None = Form(None),
        store: Repository = Depends(authenticated),
    ) -> Response:
        secure_form(request, csrf_token)
        set_tag_rule_enabled(store, rule_id, enabled == "on")
        return RedirectResponse("/tags", status_code=303)

    @app.post("/tag-rules/{rule_id}/delete")
    def tag_rule_remove(
        rule_id: int,
        request: Request,
        csrf_token: str | None = Form(None),
        store: Repository = Depends(authenticated),
    ) -> Response:
        secure_form(request, csrf_token)
        delete_tag_rule(store, rule_id)
        return RedirectResponse("/tags", status_code=303)

    @app.post("/tags/{tag_id}/delete")
    def tag_remove(
        tag_id: int,
        request: Request,
        csrf_token: str | None = Form(None),
        store: Repository = Depends(authenticated),
    ) -> Response:
        secure_form(request, csrf_token)
        delete_tag(store, tag_id)
        return RedirectResponse("/tags", status_code=303)

    @app.get("/filters", response_class=HTMLResponse)
    def filters_get(
        request: Request, store: Repository = Depends(authenticated)
    ) -> Response:
        return content_response(
            request,
            templates,
            "filters.html",
            {"rules": store.list_filter_rules()},
        )

    @app.post("/filters")
    def filter_create(
        request: Request,
        kind: str = Form(),
        phrase: str = Form(),
        csrf_token: str | None = Form(None),
        store: Repository = Depends(authenticated),
    ) -> Response:
        secure_form(request, csrf_token)
        if kind not in {"include", "exclude"}:
            raise ValueError("The filter type is invalid.")
        create_filter_rule(store, kind, phrase)  # type: ignore[arg-type]
        return RedirectResponse("/filters", status_code=303)

    @app.post("/filters/{rule_id}/toggle")
    def filter_toggle(
        rule_id: int,
        request: Request,
        enabled: str | None = Form(None),
        csrf_token: str | None = Form(None),
        store: Repository = Depends(authenticated),
    ) -> Response:
        secure_form(request, csrf_token)
        set_filter_rule_enabled(store, rule_id, enabled == "on")
        return RedirectResponse("/filters", status_code=303)

    @app.post("/filters/{rule_id}/delete")
    def filter_remove(
        rule_id: int,
        request: Request,
        csrf_token: str | None = Form(None),
        store: Repository = Depends(authenticated),
    ) -> Response:
        secure_form(request, csrf_token)
        delete_filter_rule(store, rule_id)
        return RedirectResponse("/filters", status_code=303)

    @app.get("/sources", response_class=HTMLResponse)
    def sources_get(
        request: Request, store: Repository = Depends(authenticated)
    ) -> Response:
        return content_response(
            request,
            templates,
            "sources.html",
            {
                "sources": store.list_sources(),
                "counts": store.count_posts_by_source(),
            },
        )

    @app.post("/sources/{source_id}/enabled")
    def source_enabled(
        source_id: str,
        request: Request,
        enabled: str | None = Form(None),
        csrf_token: str | None = Form(None),
        store: Repository = Depends(authenticated),
    ) -> Response:
        secure_form(request, csrf_token)
        store.set_enabled(source_id, enabled == "on")
        return RedirectResponse("/sources", status_code=303)

    return app


def content_response(
    request: Request,
    templates: Jinja2Templates,
    template: str,
    context: dict[str, object],
) -> Response:
    csrf = ensure_csrf_cookie(request)
    response = templates.TemplateResponse(
        request,
        template,
        {"request": request, "csrf_token": csrf, "authenticated": True, **context},
    )
    response.set_cookie(_CSRF_COOKIE, csrf, httponly=True, samesite="strict")
    return response


def ensure_csrf_cookie(request: Request) -> str:
    existing = request.cookies.get(_CSRF_COOKIE)
    return existing or secrets.token_urlsafe(24)


def secure_form(request: Request, supplied: str | None) -> None:
    try:
        validate_csrf(request.cookies.get(_CSRF_COOKIE), supplied)
        validate_origin(request.headers.get("origin"), _EXPECTED_ORIGIN)
    except ValueError:
        raise HTTPException(status_code=403, detail="Request is not allowed.") from None


def authenticated_or_false(store: Repository, request: Request) -> bool:
    from telegram_knowledge_base.application.auth import authenticate

    return authenticate(store, request.cookies.get(_SESSION_COOKIE))


def login_response(store: Repository, password: str) -> Response:
    token = login(store, password)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        _SESSION_COOKIE,
        token,
        max_age=_SESSION_SECONDS,
        httponly=True,
        samesite="strict",
    )
    return response
