# Test Plan — MVP-01 Инструментальная основа и безопасная конфигурация

| Field | Value |
| --- | --- |
| item | MVP-01 |
| memo | `doc/work/archive/phase-1/MVP-01-memo.md` |
| created | 2026-11-11 |
| state | green |

## Test Files

| Path | Runner | Covers |
| --- | --- | --- |
| `tests/conftest.py` | pytest | Изоляция переменных проекта и запрет сетевых операций |
| `tests/unit/config/test_settings.py` | pytest | Локальные пути, лимиты и безопасные ошибки конфигурации |
| `tests/integration/adapters/storage/test_database.py` | pytest | Начальная схема, миграция, сохранность данных и уникальность публикаций |
| `tests/integration/test_entrypoint.py` | pytest | Локальный запуск без сервера и явная ошибка конфигурации |

Контракт тестов: `load_settings` возвращает пути и лимиты; настройки задаются переменными `TKB_DATA_DIR`, `TKB_COLLECTION_LIMIT` и `TKB_PAGE_SIZE`. `initialize_database` применяет версии SQLite-схемы через `user_version`. Начальная схема предоставляет `sources` с полями `id`, `telegram_id` и `posts` с полями `source_id`, `message_id`, `text`, `published_at`. Локальная точка входа `main` возвращает код завершения и не запускает сетевые службы.

На этапе RED в `src/telegram_knowledge_base/config/settings.py`, `src/telegram_knowledge_base/adapters/storage/sqlite.py` и `src/telegram_knowledge_base/__main__.py` были добавлены заглушки, чтобы тесты падали на отсутствующем поведении, а не на ошибках импорта. На этапе реализации заглушки заменены рабочими модулями.

## Happy Path

- Значения по умолчанию помещают базу в локальный пользовательский каталог и задают согласованные лимиты.
- Локальная команда создаёт базу; повторная инициализация не удаляет сохранённые данные.
- Существующая пустая база получает начальную версию схемы.

## Privacy and Credential Safety (mandatory when tests.instructions.md requires it)

| Check | Test name |
| --- | --- |
| Unauthenticated clients cannot access private content | Веб-сервера и маршрутов нет; `test_local_entrypoint_initializes_database_without_network` с фикстурой `prevent_network` проверяет отсутствие сетевого запуска |
| Credentials/session material are absent from responses, exceptions and logs | `test_configuration_errors_do_not_disclose_environment_secrets`; `test_invalid_configuration_reports_failure_without_disclosing_secrets` используют фиктивный секрет |
| Session/configuration files are not web-served | Веб-сервера нет; пути проверяют `test_defaults_use_local_user_data_and_approved_limits` и `test_repository_data_directory_is_rejected`, отсутствие сетевого запуска — `test_local_entrypoint_initializes_database_without_network` |
| Simulated rate limits are respected without early retry or evasion | Не применимо: Telegram-запросов и повторов в MVP-01 нет. Обязательная симуляция откладывается до MVP-02 |
| Tests use no live network or real Telegram session | Автоматическая фикстура `prevent_network`; реальная сессия не создаётся и не используется |

## Edge And Degenerate Cases

| Case | Test name |
| --- | --- |
| Empty input | `test_empty_or_relative_data_directory_is_rejected`; нулевые значения в `test_invalid_limits_are_rejected` |
| Single element | Одна сохранённая публикация в `test_reinitializing_a_database_preserves_existing_posts`; минимальные лимиты в `test_local_data_override_and_boundary_limits_are_accepted` |
| All values equal | Повтор ID сообщения в `test_message_ids_are_unique_per_source` |
| Maximum realistic size | `test_local_data_override_and_boundary_limits_are_accepted`; выход за границы — `test_invalid_limits_are_rejected`. Обработки партии и страниц пока нет |
| No feasible solution | Неверная конфигурация и неизвестная новая версия схемы отклоняются с явной ошибкой |

## Deliberately Not Tested

| What | Why |
| --- | --- |
| Реальная аутентификация и доступ к страницам | В MVP-01 нет HTTP-сервера; проверки обязательны до появления маршрутов с личными данными |
| Telegram API, ожидания и повторные запросы | Адаптер и соответствующее поведение относятся к MVP-02; тесты не используют сеть |
| FTS5, фильтры, сбор партии и пагинация | Функции относятся к MVP-02—MVP-04; сейчас проверяется только конфигурация пределов |

## Run Record

| Date | Command | Result | Notes |
| --- | --- | --- | --- |
| 2026-11-11 | `python -m pytest --version` | Нет pytest в системном Python | Для запуска тестов создано изолированное окружение с pytest |
| 2026-11-11 | `.\.venv\Scripts\python.exe -m pip --version` | pip 26.3 | Обновлён по просьбе пользователя только в окружении проекта |
| 2026-11-11 | Набор pytest до добавления заглушек | 16 ошибок импорта | Пакет приложения ещё отсутствовал |
| 2026-11-11 | Набор pytest с заглушками, первый запуск | 16 упали, 1 прошёл ошибочно | Ложное прохождение исправлено и записано в Deviations memo |
| 2026-11-11 | `$env:PYTHONPATH = Join-Path (Get-Location) 'src'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'; $venvPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'; & $venvPython -m pytest -q --tb=line tests` | RED: 18 упали | Все падения вызваны `NotImplementedError` заглушек; синтаксис Python проверен Pylance |
| 2026-11-12 | `.\.venv\Scripts\python.exe -m pytest -q` | GREEN: 18 passed | Весь набор офлайн-тестов |
| 2026-11-12 | `.\.venv\Scripts\python.exe -m mypy src` | GREEN | Проверка типов |
| 2026-11-12 | `.\.venv\Scripts\python.exe -m ruff check .` | GREEN | Линтинг |
| 2026-11-12 | `.\.venv\Scripts\python.exe -m ruff format --check .` | GREEN | Проверка форматирования |
| 2026-11-12 | Два запуска `python -m telegram_knowledge_base` с `PYTHONIOENCODING=cp1252`; затем запрос `PRAGMA user_version` и списка таблиц | GREEN: оба запуска вернули 0; версия 1; таблицы `posts`, `sources` | Проверена повторная инициализация из CLI в Windows-совместимой кодировке |
| 2026-11-12 | `python -m pip wheel --no-deps --wheel-dir <temp> .` и проверка архива | GREEN | Собран wheel; начальная SQL-миграция присутствует в пакете |
