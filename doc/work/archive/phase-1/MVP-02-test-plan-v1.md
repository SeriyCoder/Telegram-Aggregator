# Test Plan — MVP-02 Управляемый сбор публикаций Telegram

| Field | Value |
| --- | --- |
| item | MVP-02 |
| memo | `doc/work/archive/phase-1/MVP-02-memo.md` |
| created | 2026-11-12 |
| state | green |

## Test Files

| Path | Runner | Covers |
| --- | --- | --- |
| `tests/conftest.py` | pytest | Изоляция окружения и запрет сети; цикл событий без сокетов |
| `tests/unit/config/test_settings.py` | pytest | Локальные пути, отклонение сетевого и синхронизируемого каталога |
| `tests/unit/application/test_sources.py` | pytest | Ручной выбор публичного канала, отказ для других источников и безопасные ошибки |
| `tests/unit/application/test_sync.py` | pytest | Последняя история, лимит, догрузка, повторы, выключенный источник, ожидание API и конкурентный запуск на фальшивых адаптерах |
| `tests/unit/adapters/telegram/test_client.py` | pytest | Запрет реального входа, разрешения источника и чтения |
| `tests/unit/adapters/telegram/test_session.py` | pytest | Сохранение в защищённом хранилище, отказ без него и сокрытие секрета |
| `tests/integration/adapters/storage/test_database.py` | pytest | Миграция версии 1 без потери публикаций |
| `tests/integration/adapters/storage/test_repository.py` | pytest | Управление источниками, транзакции, сохранённое ожидание и межпроцессная блокировка |
| `tests/integration/test_entrypoint.py` | pytest | Запуск без сервера, статус без выдачи текста публикаций и безопасный отказ Telegram-команд |

На RED добавлены только типы и заглушки без реализованного поведения в
`src/telegram_knowledge_base/domain/`, `src/telegram_knowledge_base/application/`,
`src/telegram_knowledge_base/adapters/telegram/`,
`src/telegram_knowledge_base/adapters/storage/repository.py` и
`src/telegram_knowledge_base/adapters/storage/lock.py`. Тесты определяют
контракты сценариев и хранилища; реализация может изменять внутреннее устройство,
сохраняя проверяемое поведение.

## Happy Path

- `test_manually_selected_public_channel_is_added` и
  `test_sources_can_be_enabled_and_disabled` проверяют управление источниками.
- `test_initial_sync_respects_500_limit_and_starts_with_latest` проверяет
  первичный сбор последних сообщений с максимальным лимитом 500.
- `test_backfill_and_new_posts_both_progress_with_single_message_limit` проверяет,
  что при лимите 1 не голодает ни старая, ни новая история.
- `test_version_one_database_is_migrated_without_losing_posts` проверяет миграцию
  существующей базы с публикацией.

## Privacy and Credential Safety

| Check | Test name |
| --- | --- |
| Неавторизованный доступ к содержимому | Веб-сервера нет; `test_local_entrypoint_initializes_database_without_network` и общий запрет сети проверяют локальный запуск |
| Секреты и сессия отсутствуют в ответах, исключениях и логах | `test_backend_errors_never_expose_session_material`, `test_source_access_failure_does_not_expose_secrets`, `test_telegram_commands_fail_closed_without_exposing_secrets`; проверяется также полный traceback |
| Пути и сессии не обслуживаются веб-сервером | Сервера нет; пути проверяют `test_network_data_directory_is_rejected_before_path_resolution`, `test_cloud_synced_data_directory_is_rejected` и тесты MVP-01; хранение сессии — тесты `test_session.py` |
| Ожидание API соблюдается без обхода и параллельных повторов | `test_flood_wait_survives_restart_and_forbids_early_requests`, `test_failure_to_persist_flood_wait_does_not_retry`, `test_unavailable_cooldown_storage_prevents_network_requests`, `test_cooldown_is_persisted_across_repository_instances`, `test_parallel_syncs_do_not_issue_parallel_requests`, `test_account_lock_excludes_another_process_and_is_released` |
| Нет настоящей сети или сессии | Автоматическая фикстура `prevent_network`; данные и хранилища искусственные. Дочерний процесс проверки блокировки также запрещает сетевые вызовы |
| Реальный Telegram отключён до выяснения условий | `test_real_telegram_operations_are_blocked`, `test_telegram_commands_fail_closed_without_exposing_secrets` |

Тест ожидания повторно вызывает сценарий с тем же сохранённым состоянием и
другим источником; отдельный интеграционный тест проверяет сохранение срока
в новом экземпляре репозитория. Это не является проверкой живого Telegram.

## Edge And Degenerate Cases

| Case | Test name |
| --- | --- |
| Пустая история | `test_empty_history_saves_no_posts` |
| Один элемент и лимит 1 | `test_backfill_and_new_posts_both_progress_with_single_message_limit` |
| Повтор одинакового идентификатора | `test_duplicate_batch_preserves_original_snapshot`; повтор не перезаписывает исходную копию |
| Максимальный размер | `test_initial_sync_respects_500_limit_and_starts_with_latest`; предел страницы 100 уже проверяется тестами конфигурации MVP-01 |
| Нет допустимого решения | Закрытый канал, группа, приглашение, выключенный источник, недоступное защищённое хранилище, заблокированное подключение и недоступное хранилище ожидания дают явный отказ |
| Эфемерные данные | `test_repeated_sync_keeps_existing_snapshot_and_skips_ephemeral_content` |
| Прерванная запись | `test_failed_batch_does_not_advance_cursor_and_can_be_retried`, `test_invalid_batch_rolls_back_both_posts_and_progress` |

## Deliberately Not Tested

| What | Why |
| --- | --- |
| Настоящие авторизация, Telegram API и применимость условий платформы | Реальный доступ заблокирован; пользователь разрешил пока только офлайн-разработку |
| Фактическая изоляция Windows ACL и поведение установленного Credential Manager | Тесты используют временный каталог и фальшивое хранилище; реальную изоляцию между пользователями и системный backend этот набор не доказывает |
| Структура реальных ответов Telegram и идентификация эфемерных сообщений адаптером | Пока нет разрешённого подключения; фальшивый адаптер проверяет только обработку уже помеченного сообщения |
| Веб-маршруты, FTS5, фильтры, закладки и пагинация | Относятся к MVP-03 и MVP-04, в этом пункте отсутствуют |

## Run Record

| Date | Command | Result | Notes |
| --- | --- | --- | --- |
| 2026-11-12 | `.\.venv\Scripts\python.exe -m pytest -q --tb=line tests` с `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` | Первый прогон: 27 failed, 18 passed, 17 errors | Стандартный цикл `asyncio` на Windows создавал локальную сокетную пару, заблокированную офлайн-фикстурой; исправление тестового окружения записано в memo |
| 2026-11-12 | Та же команда после исправления и дополнения тестов | RED: 33 failed, 18 passed | Заглушки дают `NotImplementedError`; существующие CLI, миграция и пути падают на отсутствующем поведении. Ошибок импорта, синтаксиса и сетевых попыток нет |
| 2026-11-12 | `.\.venv\Scripts\python.exe -m ruff check .`; `-m ruff format --check .`; `-m mypy src` | Все три проверки прошли | Форматирование, линт и типы заглушек |
| 2026-11-12 | Проверка `run_offline(asyncio.to_thread(lambda: 42))` с заблокированным `socket.bind` | 42 | Тестовый цикл исполняет задачу в потоке без создания сокетной пары |
| 2026-11-12 | `.\.venv\Scripts\python.exe -m pytest -q --tb=short tests` с `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` | GREEN: 55 passed | Полный офлайн-набор после реализации |
| 2026-11-12 | `.\.venv\Scripts\python.exe -m mypy src` | GREEN | Строгая проверка типов |
| 2026-11-12 | `.\.venv\Scripts\python.exe -m ruff check .` и `-m ruff format --check .` | GREEN | Линтинг и форматирование |
| 2026-11-12 | Проверка типа backend через `keyring.get_keyring()` | `keyring.backends.Windows.WinVaultKeyring`; защищённый backend распознан | Проверен только выбор класса, секреты не читались и не записывались |
| 2026-11-12 | Pylance `pylanceFileSyntaxErrors` | Сервис недоступен | Импорт и синтаксис проверены фактическим запуском pytest; `mypy src` прошёл |
