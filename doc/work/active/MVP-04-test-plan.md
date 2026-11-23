# Test Plan — MVP-04 Локальный защищённый браузерный интерфейс

| Field | Value |
| --- | --- |
| item | MVP-04 |
| memo | `doc/work/active/MVP-04-memo.md` |
| created | 2026-11-22 |
| state | green |

## Test Files

| Path | Runner | Covers |
| --- | --- | --- |
| `tests/unit/adapters/auth/test_passwords.py` | pytest | PBKDF2/salted verifier, минимальная длина, неверный пароль и безопасный malformed verifier |
| `tests/unit/adapters/auth/test_sessions.py` | pytest | Random opaque token и SHA-256 hash; plaintext token не сохраняется |
| `tests/unit/application/test_auth.py` | pytest | First setup, login, logout, forgery и revocation на fake AuthStore |
| `tests/unit/web/test_forms.py` | pytest | Search/filter form, tags list, CSRF exact match и exact loopback Origin |
| `tests/unit/config/test_settings.py` (добавлено) | pytest | Default web host `127.0.0.1`, fixed port 8765 и существующие локальные data limits |
| `tests/integration/adapters/storage/test_database.py` (добавлено) | pytest | Migration 3→4: verifier/sessions без потери posts/tags |
| `tests/integration/web/test_app.py` | pytest | Setup/login/logout, every route auth gate, feed/search/pagination, bookmark, tags/rules |
| `tests/integration/web/test_security.py` | pytest | CSRF, Origin, XSS, tampered cookie, static traversal, no Telegram adapter/session, security headers/redaction |
| `tests/integration/web/test_layout.py` | pytest | Semantic forms, Russian `lang`, viewport, skip link, local assets, CSS mobile layout и launcher loopback |

На RED изменён только dependency manifest web-стека, добавлены пустые
типовые модули `adapters/auth/`, `application/auth.py`, `web/app.py`,
`web/forms.py` и `AuthStore` protocol. `create_app` возвращает пустой FastAPI,
остальные функции остаются `NotImplementedError`; production routes/templates,
auth schema, CSS/JS и launcher не реализованы.

## Happy Path

- `test_first_setup_is_local_and_only_once` — пользователь один раз задаёт
  пароль на localhost; повторный setup недоступен.
- `test_wrong_password_does_not_create_a_session` — неверный пароль возвращает
  безопасную 400/401 и не выдаёт session cookie.
- `test_feed_search_and_pagination_show_only_saved_posts` — authenticated feed
  показывает сохранённый русский текст, поиск работает и не содержит offset-page
  API.
- `test_bookmark_toggle_changes_the_bookmarked_feed` — форма bookmark меняет
  состояние после redirect и `?bookmarked=on` отражает его.
- `test_tag_and_rule_forms_update_visible_feed` — пользователь создаёт тег и
  буквальное правило, затем фильтрует feed.
- `test_authenticated_shell_has_mobile_viewport_skip_link_and_local_assets` —
  GUI имеет viewport, skip link и только local static assets.
- `test_core_pages_exist_after_login` — feed/tags/filters/sources доступны
  после входа и имеют `<main>`.
- `test_css_has_mobile_layout_and_launcher_targets_loopback` — launcher и CSS
  существуют, bind только `127.0.0.1:8765`.

## Privacy and Credential Safety (mandatory when tests.instructions.md requires it)

| Check | Test name |
| --- | --- |
| Unauthenticated clients cannot access private content | `test_every_content_route_requires_authentication`; перенаправление с `/`, `/tags`, `/filters`, `/sources`; login/setup/health не выдают содержимое или пути |
| Credentials/session material are absent from responses, exceptions and logs | `test_password_verifier_is_salted_and_constant_shape`, `test_invalid_password_verifier_fails_closed_without_exposing_it`, `test_session_tokens_are_random_and_only_the_hash_is_stored_shape`, `test_login_setup_and_errors_do_not_echo_sentinel_secrets` |
| Session/configuration files are not web-served | `test_content_routes_do_not_serve_database_or_source_paths` проверяет DB, source root, `result.json` и traversal |
| Simulated rate limits are respected without early retry or evasion | Неприменимо: web route не вызывает Telegram, cooldown/retry не меняется. `test_routes_do_not_load_telegram_client` доказывает отсутствие Telegram adapter и сети. |
| Tests use no live network or real Telegram session | TestClient работает in-process; autouse `prevent_network` блокирует sockets/DNS, а Telegram/Telethon не загружается |

Дополнительно security:

- `test_post_mutation_requires_csrf_and_exact_loopback_origin` — POST без token
  или с чужим Origin отвергается.
- `test_tampered_session_cookie_cannot_access_content` — forged opaque token не
  получает доступ.
- `test_html_escapes_post_text_and_has_basic_security_headers` — user content
  autoescaped, CSP/`nosniff` включены.
- `test_logout_revokes_cookie_and_returns_to_login` и unit
  `test_logout_revokes_only_the_selected_opaque_session` — server-side session
  revocation.

## Edge And Degenerate Cases

| Case | Test name |
| --- | --- |
| Empty input | `test_empty_form_values_mean_an_unfiltered_feed`; пустой query/filters возвращает обычную ленту |
| Single element | Один session, один bookmark, одна ручная операция в app/auth/feed tests |
| All values equal | `test_wrong_password_does_not_create_a_session`, repeated setup/login/logout не создают новый verifier/session |
| Maximum realistic size | MVP-03 page limit 500 уже проверен; web test проверяет cursor pagination и POST/query parsing без отдельного huge JSON rendering |
| No feasible solution | Unauthenticated route, forged cookie, malformed password verifier, bad Origin/CSRF, setup mismatch и DB/config path traversal |

## Deliberately Not Tested

| What | Why |
| --- | --- |
| Browser/Playwright visual runtime | На RED нет UI; layout contract сначала проверяется HTTP HTML/CSS. Полный GUI smoke выполняется после GREEN вручную |
| HTTPS/LAN bind | Явно вне MVP-04; test фиксирует loopback-only |
| OAuth/multi-user/password reset email | Однопользовательский локальный MVP |
| Web upload/import | Явно вне memo; existing `result.json` импортирует технический этап |
| Electron/native installer/system tray | Явно вне memo |
| CDN/network fonts/icons | Запрещены offlining/privacy scope; tests требуют local assets |
| Download full SQLite through browser | Явно запрещено; проверяется static/path protection |

## Run Record

| Date | Command | Result | Notes |
| --- | --- | --- | --- |
| 2026-11-22 | `.venv\Scripts\python.exe -m pytest -q` | **red**: 38 failed, 148 passed | Новые web/auth tests падают на пустые FastAPI routes, `NotImplementedError`, схему 3 вместо 4, отсутствующие CSS/launcher и web-host fields. Все 148 прежних тестов зелёные. |
| 2026-11-22 | `.venv\Scripts\python.exe -m mypy src` | pass | Пустые web/auth ports и models компилируются строго. |
| 2026-11-22 | `.venv\Scripts\python.exe -m ruff check .`; `.venv\Scripts\python.exe -m ruff format --check .` | pass | — |
| 2026-11-22 | Реальная постоянная локальная база | **green**: 748 posts, 1 source | `result.json` импортирован технически в `AppData\Local`; тексты не выводились. |
| 2026-11-22 | localhost GUI smoke | **green**: `/health` 200, `/setup` 200; local setup form visible; no external assets | Server привязан только к `127.0.0.1:8765`; пароль пользователю не назначался. |
| 2026-11-22 | `.venv\Scripts\python.exe -m pytest -q` | **green**: 186 passed | Полный набор после `/3-implement`. |
| 2026-11-22 | `.venv\Scripts\python.exe -m mypy src`; `.venv\Scripts\python.exe -m ruff check .`; `.venv\Scripts\python.exe -m ruff format --check .` | pass | 31 source files; 88 files formatted. |
| 2026-11-23 | Реальный browser smoke `Origin: null` + CSRF | **green**: setup form → feed | Выполнено в отдельной disposable SQLite; база удалена, реальный server 748 posts перезапущен. |
| 2026-11-23 | `.venv\Scripts\python.exe -m pytest -q`; `.venv\Scripts\python.exe -m mypy src`; `.venv\Scripts\python.exe -m ruff check .`; `.venv\Scripts\python.exe -m ruff format --check .` | pass | 187 passed; static checks green after browser-origin fix. |
| 2026-11-23 | Browser datetime-local regression | **green**: 17 focused tests, then 189 full tests | `from=2026-11-09T06:45`/`to=2026-11-23T06:45` нормализуются из local timezone в UTC; server не возвращает 500. |
