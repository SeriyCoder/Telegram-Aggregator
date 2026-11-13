# Test Plan — MVP-02 Импорт публикаций каналов из официального экспорта Telegram

| Field | Value |
| --- | --- |
| item | MVP-02 |
| memo | `doc/work/archive/phase-1/MVP-02-memo.md` |
| created | 2026-11-13 |
| state | green |

Это второй RED-план по пункту MVP-02: первый
(`doc/work/archive/phase-1/MVP-02-test-plan-v1.md`, Telethon-основа с заблокированным
доступом) закрыт зелёным и остаётся в силе — его 55 тестов не ослабляются.
Этот план покрывает пересмотренный объём: импорт официального JSON-экспорта.

## Test Files

| Path | Runner | Covers |
| --- | --- | --- |
| `tests/unit/adapters/telegram_export/test_parser.py` | pytest | Разбор `result.json`: формат, сборка текста, время UTC, пропуски, отказы |
| `tests/unit/application/test_importing.py` | pytest | Сценарий импорта: создание источника, отчёт, отказ для отключённого и не-канала |
| `tests/integration/adapters/storage/test_repository.py` (добавлено) | pytest | `save_import`: закрытые каналы без username, идемпотентность, атомарность, неизменность курсоров |
| `tests/integration/test_entrypoint.py` (добавлено) | pytest | Команда `import`: отчёт без текста постов, повторный импорт, отказы, неизменность базы |
| `tests/fixtures/exports/*.json` | — | Синтетические экспорты: публичный и закрытый канал, пустой канал, группа, личный чат, полный экспорт, повреждённый файл |

На RED добавлены только типы и заглушки без поведения: `ChannelExport` и
`ImportReport` в `domain/models.py`, порт `ImportStore` в `application/ports.py`,
`import_channel_export` и `SourceDisabledError` в `application/importing.py`,
пакет `adapters/telegram_export/` с `parse_export`, `ExportFormatError` и
константой `MAX_EXPORT_BYTES`, методы-заглушки `source_enabled` и `save_import`
в `adapters/storage/repository.py`. Команда `import` в `__main__.py` не
добавлена: её отсутствие — часть RED.

## Happy Path

- `test_channel_export_yields_source_and_posts_with_utc_times` — экспорт канала
  даёт источник (`id`, `name`, без username) и посты со временем из
  `date_unixtime` в формате `ГГГГ-ММ-ДДTЧЧ:ММ:ССZ`.
- `test_post_text_is_assembled_from_text_entities_in_order` — текст собирается
  из частей `text_entities` в исходном порядке.
- `test_plain_text_field_is_used_when_text_entities_are_empty` — при пустых
  `text_entities` используется строковое поле `text`.
- `test_private_channel_export_is_accepted` — закрытый канал принимается.
- `test_unknown_channel_is_created_and_all_posts_count_as_new` — новый источник
  создаётся по заголовку экспорта, отчёт содержит счётчики.
- `test_import_command_reports_counts_without_printing_post_text` — команда
  `import` печатает название канала и `New/Existing/Skipped`, код выхода 0.

## Privacy and Credential Safety (mandatory when tests.instructions.md requires it)

| Check | Test name |
| --- | --- |
| Unauthenticated clients cannot access private content | Веб-сервера по-прежнему нет; действующий `test_local_entrypoint_initializes_database_without_network` подтверждает, что точка входа его не запускает. Новых маршрутов импорт не добавляет. |
| Credentials/session material are absent from responses, exceptions and logs | Импорт не использует учётные данные: `test_import_does_not_load_the_telegram_client` доказывает, что Telethon и Telegram-адаптер не загружаются. Текст постов не попадает в вывод и ошибки: `test_import_command_reports_counts_without_printing_post_text`, `test_non_channel_exports_are_refused_without_quoting_messages`, `test_corrupted_export_fails_without_changing_the_database`, `test_non_channel_exports_are_rejected_without_leaking_content`, `test_corrupted_file_is_rejected_without_quoting_file_content` |
| Session/configuration files are not web-served | Неприменимо: HTTP-сервера нет; база остаётся в `TKB_DATA_DIR` (все entrypoint-тесты работают через него). |
| Simulated rate limits are respected without early retry or evasion | Неприменимо к импорту: сетевых запросов нет; `test_import_does_not_touch_sync_cursors_or_cooldown` доказывает, что импорт не трогает cooldown и курсоры API-основы. |
| Tests use no live network or real Telegram session | Автофикстура `prevent_network` в `tests/conftest.py` действует на все новые тесты; фикстуры экспортов синтетические. |

## Edge And Degenerate Cases

| Case | Test name |
| --- | --- |
| Empty input | `test_channel_export_without_messages_yields_no_posts`, `test_empty_channel_export_reports_zero_counts` |
| Single element | `test_private_channel_export_is_accepted` (один пост) |
| All values equal | Повтор того же файла: `test_repeated_import_creates_no_duplicates_and_keeps_first_version`, `test_repeated_import_reports_existing_posts_and_adds_nothing` |
| Maximum realistic size | `test_file_above_size_limit_is_rejected_before_reading` (предел 512 МБ, проверен через подмену константы) |
| No feasible solution | Отключённый источник: `test_disabled_source_is_refused_without_writing`, `test_import_into_disabled_source_is_refused`; не-канал: `test_non_channel_exports_are_rejected_without_leaking_content`, `test_non_channel_export_is_refused_without_writing`; повреждённый файл: `test_corrupted_file_is_rejected_without_quoting_file_content`, `test_message_with_invalid_identifier_rejects_the_whole_file` |

Атомарность: `test_import_with_invalid_post_changes_nothing`,
`test_corrupted_export_fails_without_changing_the_database`.
Идемпотентность и сохранение первой версии при правке:
`test_repeated_import_creates_no_duplicates_and_keeps_first_version`,
`test_overlapping_import_reports_existing_posts`.

## Deliberately Not Tested

| What | Why |
| --- | --- |
| Реальный файл в 512 МБ | Недопустимо медленно; предел проверяется подменой константы `MAX_EXPORT_BYTES` |
| Поведение Telegram Desktop при экспорте | Чужое приложение; формат зафиксирован фикстурами по исходному коду tdesktop |
| Отказ `login`, `source add`, `sync` | Уже покрыт действующим `test_telegram_commands_fail_closed_without_exposing_secrets` |
| Изменение `.gitignore` и README | Нетестируемые артефакты; проверяются на шаге `/4-close` |
| Кодировки, отличные от UTF-8 | Официальный экспорт всегда UTF-8; не-UTF-8 файл попадает под отказ «повреждённый файл» через ошибку декодирования |

## Run Record

| Date | Command | Result | Notes |
| --- | --- | --- | --- |
| 2026-11-13 | `python -m pytest` | **red**: 30 failed, 55 passed | Новые тесты падают по ожидаемым причинам: `NotImplementedError` в заглушках `parse_export`, `import_channel_export`, `save_import`, `source_enabled`; entrypoint — `invalid choice: 'import'` (команда не существует). Все 55 прежних тестов зелёные. |
| 2026-11-13 | `python -m mypy src` | pass | Заглушки типизированы строго |
| 2026-11-13 | `python -m ruff check .` ; `python -m ruff format --check .` | pass | — |
| 2026-11-13 | `python -m pytest` | **green**: 85 passed | Реализация `/3-implement`: разборщик экспорта, сценарий импорта, `save_import`, команда `import` |
| 2026-11-13 | `python -m mypy src` ; `python -m ruff check .` ; `python -m ruff format --check .` | pass | 21 файл, строгий режим |
