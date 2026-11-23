# Memo — MVP-04 Локальный защищённый браузерный интерфейс

| Field | Value |
| --- | --- |
| item | MVP-04 |
| epic | MVP |
| phase | Phase 1 - MVP |
| status | approved |
| created | 2026-11-22 |
| approved | 2026-11-22 — пользователь принял все семь рекомендаций |
| closed | — |

## Problem

Локальная база уже импортирует посты и умеет искать, фильтровать, тегировать и
сохранять закладки, но пользователь не может просматривать результат без
командной строки. Нужен готовый браузерный GUI, который запускается на одном
компьютере, автоматически открывает localhost, сначала требует локальную
аутентификацию и никогда не публикует данные наружу.

## History

MVP-01 создал локальную SQLite и безопасную конфигурацию, MVP-02/MVP-05 добавили
официальный импорт каналов и исходных постов из связанных групп, MVP-03 добавил
теги, правила, закладки и FTS5. Технические тесты и sanity-check используют
синтетические данные и временную локальную базу. Для пользователя MVP-04 станет
первой стадией ручного GUI-тестирования; ему не нужно запускать SQL-команды,
Python-скрипты или настраивать web-развёртывание.

## Scope

**In scope**

- Локальный FastAPI-сервер, по умолчанию привязанный только к `127.0.0.1`;
  после старта браузер автоматически открывает локальный адрес. Это не
  статический `file://`-файл: сервер нужен для безопасного чтения SQLite,
  аутентификации, поиска и транзакционных действий.
- Простая команда запуска через текущую точку входа и локальный Windows launcher.
  Завершение launcher останавливает web-процесс; сервер не регистрируется как
  системная служба.
- Первая настройка через localhost-страницу: пользователь один раз задаёт пароль.
  Вход необходим для любой страницы или действия, которое содержит посты,
  теги, правила, закладки, источники или состояние базы.
- Однопользовательская аутентификация: verifier пароля хранится только как
  стойкий salted hash в локальной SQLite; cookie содержит случайный opaque
  session token, а в SQLite хранится только его SHA-256 hash и expiry. Ни пароль,
  ни session token в plaintext не сохраняются.
- Cookie локального login: `HttpOnly`, `SameSite=Strict`, ограниченный срок и
  server-side session lookup. Logout удаляет запись сессии, истечение и неверный
  пароль очищают доступ. Изменяющие POST-запросы получают CSRF-защиту и
  строгую проверку Origin.
- Server-rendered адаптивная страница-лента: текст поста, название источника,
  дата, вычисленные теги и закладка. Новый пост отображается выше при стабильной
  сортировке; пагинация использует курсор MVP-03.
- Фильтры ленты: полнотекстовый поиск, источник, диапазон дат, один/несколько
  тегов по логике OR и режим «только закладки». Пустой запрос очищает фильтр.
- Страницы тегов и правил: создать/переименовать/удалить тег, добавить/отключить
  буквальное правило, вручную назначить или снять тег у поста.
- Страница общих фильтров: создать/отключить/удалить `include`/`exclude`; каждая
  операция сразу влияет на будущую выдачу, не изменяя исходные посты.
- Управление источниками: список, количество сохранённых постов, enable/disable.
  Добавление нового источника через Telegram API остаётся заблокированным;
  импорт JSON выполняется существующей локальной командой/агентом, а не новым
  сетевым сборщиком.
- Адаптивность: usable layout без горизонтального скролла на узком телефоне,
  обычном ноутбуке и широком мониторе. Текст длинного поста переносится,
  элементы управления доступны клавиатурой и имеют понятные labels.
- Интерфейс работает без CDN и внешнего трафика: шаблоны, CSS, локальный icon/font
  fallback и небольшое JS-улучшение поставляются с приложением. При отключённом
  JS основные формы и пагинация остаются рабочими.
- Безопасная обработка ошибок: страницы и журналы не содержат текст поста,
  поисковый запрос, фразу правила, пароль, cookie, путь к базе или Telegram
  secret/session. Пользователь видит краткую локальную причину и безопасный код.
- Локальная эксплуатационная инструкция: запуск launcher, localhost URL,
  первичная установка/смена пароля, остановка, расположение базы, резервная копия
  SQLite при остановленном приложении и восстановление копии.

**Out of scope**

- Публичный сайт, VPS, домен, GitHub Pages, туннель, внешняя аутентификация,
  multi-user режим и публичный deployment.
- Автоматическое привязывание к `0.0.0.0`; LAN-доступ по умолчанию и HTTPS/PAM
  инфраструктура в текущей поставке отсутствуют.
- Telegram login/API, автоматический экспорт, загрузка файла из сети, отправка
  сообщений и обход ограничений Telegram.
- Веб-импорт большого `result.json`, REST API для внешних клиентов, AI, semantic
  search, рекомендация тем, медиапросмотр и комментарии участников.
- Desktop native UI/Electron/запуск из системного трей; launcher остаётся локальным
  Windows-скриптом, открывающим браузер.
- Резервное облачное хранение, автоматический backup по расписанию и удалённое
  восстановление.

## Approach

MVP-04 использует серверный стек из спецификации: FastAPI получает запрос,
Jinja2 отображает HTML, Uvicorn слушает loopback, SQLite Repository отвечает за
данные. Web-handler не импортирует Telegram adapter/session и получает только
прикладные сценарии знаний. Маршруты работают отдельным слоем над
`application.knowledge`: они не дублируют SQL и не вызывают Repository напрямую
в шаблонах.

Публично доступными до входа будут только landing/login/setup/logout/health
поверхности без данных. Setup разрешён только пока verifier не создан и только
на запросе loopback; после настройки любой content-route применяет одинаковую
dependency аутентификации. При старте создаётся verifier, после успешного
входа выдаётся случайный opaque cookie, а его hash и expiry хранятся в SQLite.
Cookie не несёт текст поста, пароль, путь к базе или Telegram-сессию.

Пароль проверяется в constant-time операции над сохранённым salted hash. Session
token создаётся криптографическим генератором случайных байтов; в browser
показывается только cookie, а в SQLite — SHA-256 hash и expiry. Logout удаляет
server-side запись, поэтому старый cookie немедленно перестаёт работать.
Дополнительный signing secret/keyring для web не нужен.

Все POST-формы содержат CSRF-token, привязанный к сессии; маршруты отвергают
неверный Origin/Referer до изменения данных. Пользовательский текст проходит
Jinja autoescape и не используется как raw HTML/JavaScript/SQL. Query-параметры
строят `PostQuery`, поэтому поиск, даты и пагинация проходят доменную
валидацию MVP-03. Операции tag/bookmark/source используют прикладные функции и
после успешного POST возвращают redirect, предотвращающий повторное действие
при refresh.

Интерфейс собирается как небольшой серверный сайт без CDN. Локальная CSS-сетка
поддерживает desktop/mobile; встроенный `details`/forms обеспечивает базовую
работу без JavaScript. Небольшой локальный скрипт может улучшать только
keyboard/focus и подтверждение действий, но не становится необходимостью для
просмотра или сохранения данных. Сервер не отдаёт `TKB_DATA_DIR`, миграции,
`result.json`, Python-исходники или корень файловой системы.

Launcher запускает единственный Uvicorn-процесс на фиксированном loopback-порте
8765, открывает браузер после health-check и выводит локальный адрес. OS-level
lock-файл в `TKB_DATA_DIR` не позволяет повторному запуску создать второй сервер.
Если сервер уже запущен, launcher только открывает его страницу; stale lock
автоматически освобождается после завершения процесса. `LAN` и `public
deployment` не являются возможностями launcher.

**Rejected alternative:** статический HTML с копией SQLite в браузере — это
выдаёт всю базу любому читателю файла, усложняет миграции и не имеет надёжной
аутентификации, поиска и транзакционных действий.

**Rejected alternative:** SPA, загружающая CDN-пакеты или внешний UI-хост —
нарушает офлайн-запуск, приватность и воспроизводимость локальной установки.

**Rejected alternative:** автоматически слушать LAN/`0.0.0.0` — пользователь не
просил deployment, а пароли по нешифрованному LAN HTTP создают отдельный риск
перехвата; расширение требует собственного пункта.

## Data / Schema Delta

| Entity / field | Change | Version or migration impact |
| --- | --- | --- |
| `web_auth` | Один локальный verifier: salt, password hash, PBKDF2 parameters, created/changed time | Миграция `0004` |
| `web_sessions` | Хэш случайного opaque cookie, expiry и время создания; logout удаляет запись | Новая таблица в миграции `0004` |
| `posts/tags/filter_rules/manual_post_tags/bookmarks` | Только читаются/изменяются существующими Repository API | Без изменения данных/колонок |
| `sources.enabled` | Изменяется через защищённый route enable/disable | Без изменения схемы |
| Launcher lock | OS-level lock в `TKB_DATA_DIR`, фиксированный loopback port 8765 | Локальное временное состояние; lock освобождается системой |

## Interface Delta

- Новая команда `web` в локальной точке входа, параметры `--host/--port` не
  принимаются из web UI; production host override не добавляется. Команда
  инициализирует БД и запускает только loopback.
- Windows launcher `scripts/start_gui.ps1` выполняет команду `web`, автоматически
  открывает браузер и остаётся в foreground, чтобы завершение окна консоли
  останавливал сервер.
- Routes: setup/login/logout, лента, full-text search/filtering, закладки,
  управление тегами/правилами, ручное назначение тега, управление состоянием
  источника и health без приватных данных.
- Текущие CLI-команды `import`, `status`, `source list|enable|disable` сохраняют
  поведение; `login`, `source add`, `sync` Telegram по-прежнему явно отказывают.
- HTML templates/CSS/local JS поставляются как package data. `file://` не
  поддерживается и не объявляется основной поверхностью.
- Backup/restore выполняются локальным процессом копирования остановленной
  SQLite; HTTP route для скачивания полной базы не добавляется.

## Privacy and Credential Safety

| Question | Answer |
| --- | --- |
| Is any Telegram credential or session material introduced, moved or exposed? | Нет. Web-layer получает только `KnowledgeStore`/AuthStore/Repository; Telegram adapter, API credentials и Telegram session objects не импортируются и не передаются в dependency/templates. Локальная web-session — отдельный opaque cookie, в DB сохраняется только его hash. |
| Can an unauthenticated client reach any content-bearing route or file? | Нет. Все content routes применяют одну auth dependency; setup/login/health не возвращают посты, теги, правила, статистику базы или paths. |
| Does the change alter where local data or session files are stored? | База остаётся в проверенном `TKB_DATA_DIR`; password verifier и web-session hash находятся в ней, static/templates — tracked package assets. Файлы не поддаются из static routes. |
| Could an error, log, template or response reveal secrets or private content? | Jinja autoescape, безопасные generic errors и редактирование логов исключают пароль, cookie, search/rule text, post text и local path; тесты используют sentinel values. |
| Does the change affect rate-limit handling or remote connectivity? | Нет прямых запросов к Telegram и внешним сервисам. Сервер слушает `127.0.0.1`, LAN/public binding отсутствует, CDN отсутствует. |
| How it is proven by tests | Автофикстура запрещает сеть; TestClient проверяет auth gate на каждой content route, setup once, logout/cookie tamper/expiry/revocation, CSRF, Origin, XSS autoescape, отсутствия Telegram session, loopback bind, static path protection, CRUD UI и mobile/desktop HTML structure. |

## Files

| Path | Change |
| --- | --- |
| `pyproject.toml` | FastAPI, Uvicorn, Jinja2, python-multipart; dev HTTP/test client dependencies и package data |
| `src/telegram_knowledge_base/config/settings.py` | Настройки web: loopback host/port/expiry только в локальном безопасном диапазоне |
| `src/telegram_knowledge_base/adapters/storage/migrations/0004_web_auth.sql` | Локальный password verifier без plaintext |
| `src/telegram_knowledge_base/adapters/storage/sqlite.py` | Schema version 4 |
| `src/telegram_knowledge_base/adapters/auth/` | Password hash verification, random session token и hash, без keyring |
| `src/telegram_knowledge_base/application/auth.py` | Сценарии first setup/login/logout/expiry для web adapter |
| `src/telegram_knowledge_base/application/ports.py` | Auth/session port для отделения web от storage |
| `src/telegram_knowledge_base/adapters/storage/repository.py` | Store verifier/sessions, source post counts и безопасные metadata methods, без Telegram/session objects |
| `src/telegram_knowledge_base/web/__init__.py` | Пакет web |
| `src/telegram_knowledge_base/web/app.py` | FastAPI app factory и маршруты; loopback/auth/CSRF dependencies |
| `src/telegram_knowledge_base/web/dependencies.py` | Auth, repository и safe request dependencies |
| `src/telegram_knowledge_base/web/forms.py` | Валидация query/form input и безопасные user errors |
| `src/telegram_knowledge_base/web/templates/base.html` | Общий shell, skip-link, CSP, meta viewport |
| `src/telegram_knowledge_base/web/templates/setup.html` | Первая локальная установка пароля |
| `src/telegram_knowledge_base/web/templates/login.html` | Локальный вход/ошибка |
| `src/telegram_knowledge_base/web/templates/feed.html` | Лента, поиск, фильтры, пагинация, tags/bookmark |
| `src/telegram_knowledge_base/web/templates/tags.html` | Создание/правка/правила/ручные назначения тегов |
| `src/telegram_knowledge_base/web/templates/filters.html` | include/exclude rules |
| `src/telegram_knowledge_base/web/templates/sources.html` | Источники, counts, enable/disable |
| `src/telegram_knowledge_base/web/static/app.css` | Responsive/accessibility styling |
| `src/telegram_knowledge_base/web/static/app.js` | Минимальное progressive enhancement без CDN |
| `scripts/start_gui.ps1` | Windows launcher, открывающий localhost browser |
| `src/telegram_knowledge_base/__main__.py` | Команда `web`, lifecycle, port/open-browser |
| `tests/unit/adapters/auth/` | Password/KDF, random token и session hash |
| `tests/unit/web/test_forms.py` | Валидация query/form/CSRF/Origin |
| `tests/integration/web/test_app.py` | Auth gate, setup/login/logout, cookie tamper/expiry, routes, CRUD и absence Telegram client |
| `tests/integration/web/test_security.py` | XSS, CSRF, path/static/config leaks, redaction, loopback-only bind |
| `tests/integration/web/test_layout.py` | Semantic labels, mobile/desktop HTML structure, no external URL/assets |
| `README.md` | Launcher, first login, backup/restore, localhost boundary |
| `doc/spec/telegram-knowledge-base.md` | Текущее состояние MVP-04 и критерии локального GUI |
| `.github/copilot-instructions.md` | Локальный launcher и отсутствие public deployment |
| `doc/backlog.md` | Закрытие MVP-04; при необходимости отдельный будущий LAN/TLS пункт |
| `doc/work/active/MVP-04-memo.md`, `doc/work/active/MVP-04-test-plan.md`, `doc/work/STATUS.md` | Артефакты цикла |

## Definition of Done

- [ ] Новые тесты написаны первыми и показали ожидаемое падение
- [ ] Launcher запускает один локальный server и открывает browser; повторный
  запуск не создаёт второй процесс
- [ ] Default bind — только `127.0.0.1`; нет публичного/LAN/CDN endpoint
- [ ] Setup/password/login/logout/cookie tamper/expiry/revocation работают;
  plaintext password и raw cookie token не сохраняются
- [ ] Каждая content route отклоняет неаутентифицированного пользователя
- [ ] POST-операции защищены CSRF и Origin; ошибки не выдают пароль, cookie,
  post/rule/search text, path или Telegram secret/session
- [ ] Лента показывает текст, источник, дату, computed tags/bookmark и корректную
  cursor pagination
- [ ] Поиск, источник, даты, теги и bookmarks-комбинации работают из GUI
- [ ] User may create/edit/delete tags/rules/manual tags, include/exclude filters
  и toggle bookmark/source; каждая операция отражается после redirect
- [ ] Основные формы работают без JavaScript; мобильный и desktop layout не
  требуют horizontal scroll, имеют labels/keyboard/focus/skip-link
- [ ] Telegram adapter/session ни один route не импортирует и не вызывает сеть
- [ ] README объясняет запуск, первый пароль, stop, local backup/restore
- [ ] Реальные 748 локально импортированных постов проходят ручной smoke в
  GUI: login, search, tag, bookmark, pagination; текст не попадает в test logs
- [ ] Suite, type check, lint и format green
- [ ] Deviations и изменения backlog зафиксированы

## Open Questions — решены 2026-11-22

1. Это локальный файл `file://` или локальный web-сервер? — **Решение:**
   loopback web-сервер. Статический файл не может безопасно работать с SQLite,
   auth, FTS, bookmark и CSRF; пользователь видит его как обычную вкладку браузера,
   но данные остаются локальными.
2. Как пользователь получает доступ после первого запуска? — **Решение:**
   launcher открывает localhost setup/login; пароль задаётся один раз. Verifier
   и hash server-side session хранятся локально в SQLite; plaintext password и
   cookie token в базе не появляются.
3. Нужно ли автоматически слушать LAN на этапе MVP-04? — **Решение:** нет.
   Только `127.0.0.1` без TLS. LAN/TLS оставить отдельным пунктом, чтобы не
   обещать безопасное развёртывание незашифрованного локального HTTP.
4. Нужен ли импорт `result.json` через браузер? — **Решение:** нет в
   MVP-04. Техническую загрузку выполняет агент/локальная существующая команда;
   web scope — защищённый просмотр и управление сохранёнными данными.
5. Использовать SPA/CDN или server-rendered HTML? — **Решение:**
   server-rendered Jinja, CSS и минимальный local JS. Страница работает offline и
   без JS; CDN и отдельный frontend build не добавляются.
6. Нужно ли выпускать установщик/desktop native UI? — **Решение:** нет.
   MVP-04 — Windows launcher + browser; Electron/PWA/tray — отдельный объём.
7. Можно ли скачивать полную SQLite базу через web? — **Решение:** нет.
   Backup выполняется на остановленном процессе локальным copying, иначе
   consistency/auth и accidental exposure усложняются.

## Deviations

| Step | Deviation | Reason |
| --- | --- | --- |
| `/2-tests` | TestClient использует существующий `OfflineEventLoop` через `backend_options.loop_factory` | Windows ProactorEventLoop создаёт внутреннюю socket pair, которую общий fixture запрета сети справедливо блокировал; ASGI остаётся in-process и реальной сети нет |
| `/3-implement` | Тест schema 2→3 теперь проверяет итоговую текущую версию 4, потому что `initialize_database` применяет все доступные миграции | GUI auth добавил `0004_web_auth`; прежний red assertion версии 3 проверял промежуточное состояние, а не актуальный результат |
| `/3-implement` | Неудачный login дополнительно отзывает уже существующую локальную session cookie | Это закрывает двусмысленный переход из setup уже аутентифицированного клиента и не позволяет неверной попытке оставить прежнюю сессию активной |
| `/3-implement` | Bookmark-тест исправлен с фиктивного `PYTHON` на фактический текст синтетической записи `Python новости` | GUI обязан показывать исходный текст без изменения регистра; прежнее ожидание было несогласовано с fixture и не отражало product contract |
| `/3-implement` | Privacy-тест web проверяет только modules, загруженные запросом, а не весь prior process state | В полном suite Telegram modules были загружены прежними тестами; тест должен доказывать отсутствие нового импорта web-layer, как в MVP-05, а не исходную чистоту общего pytest process |
| `/3-implement` | `Origin: null` принимается только вместе с совпавшим CSRF cookie/form token | Реальный встроенный браузер VS Code отправляет opaque origin для localhost POST; CSRF остаётся обязательным, `null` не разрешает доступ без локального double-submit token, а обычные внешние Origin продолжают отклоняться |
| `/3-implement` | `datetime-local` web-форма нормализуется из локального timezone компьютера в UTC на web-границе | Реальный браузер отправляет `2026-11-09T06:45` без суффикса `Z`, тогда как доменный query требует timezone; конверсия устраняет 500 без ослабления domain validation |
