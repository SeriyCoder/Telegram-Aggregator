# Test Plan — MVP-05 Импорт исходных постов из группы обсуждения

| Field | Value |
| --- | --- |
| item | MVP-05 |
| memo | `doc/work/archive/phase-1/MVP-05-memo.md` |
| created | 2026-11-22 |
| state | green |

## Test Files

| Path | Runner | Covers |
| --- | --- | --- |
| `tests/fixtures/exports/discussion_group.json` | — | Синтетический публичный supergroup: два исходных поста канала, участник-комментатор, чужая пересылка, служебная запись и пост только с медиа |
| `tests/unit/adapters/telegram_export/test_parser.py` | pytest | Тип `DISCUSSION_GROUP`, отбор `saved_from`-постов, подпись к фото, UTC, публичная/закрытая группа, безопасный отказ для произвольной группы |
| `tests/unit/application/test_importing.py` | pytest | Принятие только проверенного типа, отключённый источник, сохранение исходных постов без данных комментариев и счётчики |
| `tests/integration/adapters/storage/test_repository.py` | pytest | Хранение группы как источника, идемпотентность, сохранение первой версии и атомарность |
| `tests/integration/test_entrypoint.py` | pytest | Команда `import`, `Source:`, безопасные счётчики, повторный импорт, отсутствие Telegram-адаптера, имён, ID участников и текста в выводе |

На RED добавлен только типовой маркер `ExportKind` и поле `ChannelExport.kind`;
логика разборщика, сценария, хранилища и точки входа не изменена.

## Happy Path

- `test_discussion_group_selects_only_original_channel_posts` — из шести записей
  выбираются ровно два исходных поста канала; комментарий, чужая пересылка,
  служебная запись и пост без текста считаются `Skipped`.
- `test_discussion_group_keeps_original_post_times_in_utc` — время каждого
  выбранного поста переводится из `date_unixtime` в UTC без локального смещения.
- `test_private_discussion_group_is_accepted` — закрытая супер-группа принимает
  тот же узкий контракт, что и публичная.
- `test_discussion_channel_posts_are_imported_without_comment_data` — сценарий
  передаёт только выбранные посты и возвращает `New/Existing/Skipped`.
- `test_discussion_group_import_reports_only_safe_counts` — CLI успешно
  импортирует синтетическую группу, печатает нейтральное `Source:` и числа.

## Privacy and Credential Safety (mandatory when tests.instructions.md requires it)

| Check | Test name |
| --- | --- |
| Unauthenticated clients cannot access private content | Невозможный путь: веб-сервер не существует. Действующие `test_local_entrypoint_initializes_database_without_network` и новые entrypoint-тесты подтверждают локальный CLI без запуска сервера. |
| Credentials/session material are absent from responses, exceptions and logs | `test_discussion_group_marker_requires_channel_forward_identifier`, `test_discussion_group_import_reports_only_safe_counts`, `test_unmarked_group_refusal_does_not_reveal_members_or_comments`: текст, имя и ID синтетического участника не появляются в ошибках/выводе. `test_discussion_import_does_not_load_telegram_or_network_adapter` запрещает загрузку Telegram-клиента. |
| Session/configuration files are not web-served | Неприменимо: нет web/static routes; база остаётся в проверенном `TKB_DATA_DIR`, путь и сессия не выдаются. |
| Simulated rate limits are respected without early retry or evasion | Неприменимо: импорт только локального файла; сетевых запросов и retry-пути нет. Действующий тест `test_import_does_not_touch_sync_cursors_or_cooldown` остаётся в наборе. |
| Tests use no live network or real Telegram session | Автофикстура `prevent_network` в `tests/conftest.py` блокирует сеть на каждый тест. Фикстура полностью синтетическая; реальный `result.json` не копируется в тесты. |

## Edge And Degenerate Cases

| Case | Test name |
| --- | --- |
| Empty input | Канал без выбранных постов: существующий `test_channel_export_without_messages_yields_no_posts`; супер-группа без валидных исходных постов: `test_discussion_group_without_selected_posts_is_rejected` |
| Single element | Один пост без соответствующего исходному каналу маркера: `test_discussion_group_marker_requires_channel_forward_identifier` |
| All values equal | Повтор импорта: `test_repeated_discussion_import_preserves_the_first_post_version`, `test_repeated_discussion_group_import_reports_existing_posts` |
| Maximum realistic size | Действующий `test_file_above_size_limit_is_rejected_before_reading` проверяет лимит 512 МБ через подмену константы. Реальный файл 45,32 МБ будет использован только отдельной локальной sanity-проверкой после GREEN, не тестовой фикстурой. |
| No feasible solution | Произвольная/неразмеченная группа: `test_unverified_non_channel_export_is_still_rejected`, `test_unmarked_group_refusal_does_not_reveal_members_or_comments`; повреждённый хранилищный импорт: `test_invalid_discussion_import_rolls_back_source_and_posts` |

Дополнительные граничные проверки:

- `test_discussion_group_result_has_no_participant_fields` — предметные посты не
  содержат автора, ID автора, reply-связь или реакции.
- `test_discussion_import_does_not_load_telegram_or_network_adapter` — даже
  успешный импорт группы не загружает Telethon/Telegram-адаптер.
- `test_discussion_group_can_store_original_channel_posts` — в схеме SQLite нет
  новой пользовательской сущности и отдельной миграции.

## Deliberately Not Tested

| What | Why |
| --- | --- |
| Реальные 34 439 сообщений пользователя | Персональные данные не копируются в репозиторий; после GREEN выполняется только локальный sanity-check с агрегированными числами |
| Распознавание всего диапазона странных сторонних JSON | Поддерживается официальный формат Telegram Desktop и минимальная безопасная структура |
| Извлечение участников, replies и реакций | Явно вне MVP-05; будущий пункт после него |
| Дедупликация между прямым экспортом канала и экспортом группы | В группе нет надёжного исходного `message_id`; эти пути намеренно считаются разными источниками |
| OCR, транскрибация и файлы медиа | Явно вне спецификации MVP; сохраняется только текстовая подпись |
| Управление Telegram Desktop или сеть | Запрещено контуром; экспорт создаёт пользователь вручную |

## Run Record

| Date | Command | Result | Notes |
| --- | --- | --- | --- |
| 2026-11-22 | `.venv\Scripts\python.exe -m pytest -q` | **red**: 11 failed, 89 passed | Новые тесты падают по ожидаемым причинам: parser принимает только типы каналов, сценарий отклоняет `is_channel=False`, storage требует канал, а CLI не принимает discussion-group экспорт. Прежние проверки остаются зелёными. |
| 2026-11-22 | `.venv\Scripts\python.exe -m mypy src` | pass | Типовой маркер RED компилируется в строгом режиме. |
| 2026-11-22 | `.venv\Scripts\python.exe -m ruff check .` | pass | — |
| 2026-11-22 | `.venv\Scripts\python.exe -m ruff format --check .` | pass | Один тестовый файл автоматически отформатирован; ожидания не менялись. |
| 2026-11-22 | Реальный `result.json` 45,32 МБ в изолированной временной базе | **green**: `New: 748`, `Existing: 0`, `Skipped: 33691`; повтор: `New: 0`, `Existing: 748` | База находилась вне проекта и OneDrive; удалена после проверки. Тексты и участники не выводились. |
| 2026-11-22 | `.venv\Scripts\python.exe -m pytest -q` | **green**: 100 passed | Полный набор после `/3-implement`. |
| 2026-11-22 | `.venv\Scripts\python.exe -m mypy src`; `.venv\Scripts\python.exe -m ruff check .`; `.venv\Scripts\python.exe -m ruff format --check .` | pass | 21 source file; 64 files formatted. |
