# Test Plan — MVP-03 Правила отбора, теги, закладки и полнотекстовый поиск

| Field | Value |
| --- | --- |
| item | MVP-03 |
| memo | `doc/work/archive/phase-1/MVP-03-memo.md` |
| created | 2026-11-22 |
| state | green |

## Test Files

| Path | Runner | Covers |
| --- | --- | --- |
| `tests/unit/domain/test_filtering.py` | pytest | Unicode-нормализация тега/фразы, безопасные поисковые токены, пустой ввод, лимиты, даты и курсор |
| `tests/unit/application/test_knowledge.py` | pytest | Прикладные контракты создания тегов/правил/фильтров, ручных тегов, закладок и запроса |
| `tests/fixtures/knowledge/russian_posts.json` | — | Синтетические русские посты, повторяющиеся даты, специальные строки и два источника |
| `tests/integration/adapters/storage/test_database.py` | pytest | Миграция 2→3, backfill существующих постов, таблицы FTS/knowledge, атомарный отказ без FTS5 |
| `tests/integration/adapters/storage/test_repository.py` | pytest | CRUD, автотеги, ручные теги, include/exclude, FTS, закладки, даты, стабильная пагинация и синхронизация |

На RED добавлены только типовые модели в `domain/models.py`, протокол
`KnowledgeStore`, пустой модуль `domain/filtering.py`, функции-заглушки
`application/knowledge.py` и методы-заглушки в `Repository`. Никакая логика
поиска, тегов, миграции 3 или FTS не реализована.

## Happy Path

- `test_tag_keys_are_stable_unicode_names` и
  `test_create_tag_normalizes_a_private_label_only_at_boundary` — тег создаётся
  из собственного имени пользователя, хранит читаемое имя и устойчивый ключ.
- `test_tags_can_be_created_from_scratch_and_listed` — пустой каталог начинает
  работу без встроенных тем.
- `test_automatic_tags_recompute_for_existing_posts_and_respect_enabled` —
  создание/отключение правила меняет вычисленный тег уже сохранённых постов.
- `test_manual_tag_survives_disabling_automatic_rule` — ручной тег остаётся даже
  после отключения совпавшего автоправила.
- `test_filter_include_rules_are_or_and_exclude_is_applied_after` — несколько
  `include` дают OR, а `exclude` применяется к итоговой выдаче.
- `test_full_text_search_handles_cyrillic_case_and_and_tokens` — кириллица,
  регистр и AND по словам работают через SQLite FTS5.
- `test_bookmarks_are_idempotent_and_can_filter_the_feed` — повтор операции не
  создаёт дублей, фильтр возвращает только сохранённые посты.
- `test_query_combines_source_date_search_tag_and_bookmark` — единый запрос
  комбинирует все границы MVP-03.
- `test_version_two_database_backfills_search_and_knowledge_schema` — миграция
  2→3 переносит существующий пост и создаёт полный индекс.

## Privacy and Credential Safety (mandatory when tests.instructions.md requires it)

| Check | Test name |
| --- | --- |
| Unauthenticated clients cannot access private content | Неприменимо на границе UI: MVP-03 не создаёт HTTP/web routes. Действующие entrypoint-тесты подтверждают, что CLI не запускает сервер; новые методы доступны только локальным offline-фейкам/Repository. |
| Credentials/session material are absent from responses, exceptions and logs | `test_tag_keys_are_unique_without_text_in_the_error`, `test_invalid_tag_rule_is_refused_without_calling_store`, `test_search_results_do_not_expose_commenter_fields_or_file_paths` проверяют отсутствие имён, приватных фраз и локального пути в ошибках/результатах. Telegram credentials отсутствуют в API. |
| Session/configuration files are not web-served | Неприменимо: web/static routes нет. Схема знаний остаётся в текущей SQLite базе `TKB_DATA_DIR`; тесты не создают копию конфигурации. |
| Simulated rate limits are respected without early retry or evasion | Неприменимо: изменения только локального поиска. `test_query_does_not_touch_sync_cursors_or_cooldown` доказывает, что KnowledgeStore не меняет `sync_state` и `api_cooldown`. |
| Tests use no live network or real Telegram session | Автофикстура `prevent_network` запрещает сокеты/DNS. Все данные синтетические; Telegram-адаптер не вызывается. |

## Edge And Degenerate Cases

| Case | Test name |
| --- | --- |
| Empty input | `test_empty_or_punctuation_only_search_has_no_tokens`, `test_empty_search_query_returns_the_unsearched_filtered_feed`, `test_empty_tag_name_is_rejected`, `test_empty_literal_phrase_is_rejected` |
| Single element | Один ручной тег после отключения автоправила: `test_manual_tag_survives_disabling_automatic_rule`; один bookmark: `test_bookmarks_are_idempotent_and_can_filter_the_feed` |
| All values equal | Три поста с одинаковой датой и стабильный порядок: `test_pagination_is_stable_for_equal_dates_and_has_no_duplicates` |
| Maximum realistic size | Предел страницы 500 проверяется `test_query_rejects_invalid_page_size_and_dates`; 748 реальных постов покрываются атомарным backfill после GREEN, как в Definition of Done |
| No feasible solution | Нет FTS5: `test_unavailable_fts5_rejects_migration_without_partial_changes`; нет совпадений: `test_search_treats_special_input_as_literal_text_not_syntax`; нет выбранных тегов после отключения правила: `test_automatic_tags_recompute_for_existing_posts_and_respect_enabled` |

Дополнительные boundary cases:

- `test_search_text_becomes_safe_unicode_tokens_without_operators` и
  параметризованный `test_search_treats_special_input_as_literal_text_not_syntax`
  проверяют, что `OR`, `AND`, скобки и кавычки не становятся операторами FTS.
- `test_fts_stays_in_sync_after_insert_update_and_delete` защищает от drift
  между `posts` и FTS.
- `test_disabling_the_only_include_filter_restores_non_excluded_posts`
  проверяет поведение «нет активных include».
- `test_multiple_selected_tags_are_combined_with_or` фиксирует OR для выбранных
  тегов.

## Deliberately Not Tested

| What | Why |
| --- | --- |
| Инициалы автора и фильтрация людей | Комментарии/участники — FUTURE-03, таких данных сейчас нет |
| HTML, browser layout, authentication routes | MVP-04 |
| Сложный язык запросов, stemming, morphology, relevance ranking | Явно вне MVP; Unicode-токены AND и порядок по дате |
| AI-теги, embeddings, cloud APIs | Запрещены границей приватности и out of scope |
| Реальные пользовательские посты как fixture | Не копируются в репозиторий; после GREEN только агрегатная миграция/поиск sanity check |
| Вывод содержимого через CLI | Намеренно отсутствует до защищённого GUI |

## Run Record

| Date | Command | Result | Notes |
| --- | --- | --- | --- |
| 2026-11-22 | `.venv\Scripts\python.exe -m pytest -q` | **red**: 48 failed, 100 passed | Новые контракты падают по ожидаемым причинам: domain/application/repository methods остаются `NotImplementedError`, schema version не достигает 3, FTS/knowledge tables отсутствуют. Все 100 прежних тестов зелёные. |
| 2026-11-22 | `.venv\Scripts\python.exe -m mypy src` | pass | Типовые модели, порты и заглушки компилируются строго. |
| 2026-11-22 | `.venv\Scripts\python.exe -m ruff check .`; `.venv\Scripts\python.exe -m ruff format --check .` | pass | — |
| 2026-11-22 | Реальные 748 постов: временная schema v2 → schema v3 | **green**: Version=3, Imported=748, Indexed=748, SearchMatches=5 | Только агрегаты; база вне проекта и OneDrive удалена после проверки. |
| 2026-11-22 | `.venv\Scripts\python.exe -m pytest -q` | **green**: 148 passed | Полный набор после `/3-implement`. |
| 2026-11-22 | `.venv\Scripts\python.exe -m mypy src`; `.venv\Scripts\python.exe -m ruff check .`; `.venv\Scripts\python.exe -m ruff format --check .` | pass | 23 source files; 70 files formatted. |
