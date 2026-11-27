# Test Plan — FUTURE-04 Локальная контекстная система тегов

| Field | Value |
| --- | --- |
| item | FUTURE-04 |
| memo | `doc/work/active/FUTURE-04-memo.md` |
| created | 2026-11-27 |
| state | red |

## Test Files

| Path | Runner | Covers |
| --- | --- | --- |
| `tests/unit/domain/test_tagging.py` | pytest | Одно отображение тега при нескольких происхождениях, confidence boundary, ручная блокировка и дедупликация 500 повторов |
| `tests/integration/adapters/storage/test_database.py` | pytest | Миграция 4→5 и сохранение существующего ручного назначения |
| `tests/integration/web/test_app.py` | pytest | Три представления каталога тегов после authenticated setup |

## Happy Path

- `test_same_tag_is_visible_once_with_all_origins_preserved` — ручное,
  правиловое и контекстное назначение дают один эффективный тег с тремя
  причинами.
- `test_context_preview_accepts_threshold_and_deduplicates_maximum_batch` —
  точная граница confidence допускается, низкая confidence не допускается,
  повтор 500 одинаковых кандидатов возвращается один раз.
- `test_manual_block_excludes_only_selected_post_tag_from_context_preview` —
  блокировка действует на одну пару «пост + тег» и не скрывает другие посты.
- `test_version_four_database_migrates_manual_tags_to_context_schema` — schema 5
  создаётся, старое ручное назначение переносится с provenance `manual`.
- `test_authenticated_tag_catalogue_exposes_all_mine_and_suggestions_views` —
  после входа GUI показывает единый каталог и три представления.

## Privacy and Credential Safety (mandatory when tests.instructions.md requires it)

| Check | Test name |
| --- | --- |
| Unauthenticated clients cannot access private content | Существующий `test_every_content_route_requires_authentication`; RED-набор добавляет `/tags?view=suggestions` |
| Credentials/session material are absent from responses, exceptions and logs | Существующие web security tests; новый каталог не добавляет отдельную обработку credentials/session |
| Session/configuration files are not web-served | Существующий `test_content_routes_do_not_serve_database_or_source_paths`; tagging view использует тот же authenticated app/static boundary |
| Simulated rate limits are respected without early retry or evasion | Неприменимо: FUTURE-04 не вызывает Telegram и не меняет retry/cooldown |
| Tests use no live network or real Telegram session | Autouse `prevent_network`; domain и GUI tests используют синтетические записи без Telegram adapter/session |

## Edge And Degenerate Cases

| Case | Test name |
| --- | --- |
| Empty input | `test_empty_context_preview_has_no_assignments` |
| Single element | `test_manual_block_excludes_only_selected_post_tag_from_context_preview` |
| All values equal | `test_context_preview_accepts_threshold_and_deduplicates_maximum_batch` |
| Maximum realistic size | 500 одинаковых assignment candidates в одном preview — текущий установленный верхний лимит MVP-01 |
| No feasible solution | Все кандидаты ниже порога либо заблокированы; preview пуст, ничего не применяется |

## Deliberately Not Tested

| What | Why |
| --- | --- |
| Качество семантической классификации на реальном корпусе | В RED фиксируется контракт и ограничения, а качество движка оценивается позднее по синтетическим понятным текстам и ручному smoke |
| Планировщик, автоматический запуск после импорта и отмена задания | Явно FUTURE-06 |
| Скачиваемая/облачная модель, Gemini, NotebookLM и сеть | Явно вне FUTURE-04 |
| Полный визуальный дизайн | Покрывается HTML contract и ручным smoke; не требуется для контекстного ядра |
| Любой реальный Telegram source/session | Тесты офлайн и не должны требовать credentials |

## Run Record

| Date | Command | Result | Notes |
| --- | --- | --- | --- |
| 2026-11-27 | `.venv\Scripts\python.exe -m pytest -q tests\unit\domain\test_tagging.py tests\integration\adapters\storage\test_database.py::test_version_four_database_migrates_manual_tags_to_context_schema tests\integration\web\test_app.py::test_authenticated_tag_catalogue_exposes_all_mine_and_suggestions_views` | **red**: 6 failed | Четыре ожидаемых `NotImplementedError`, schema осталась 4 вместо 5, GUI не содержит три представления каталога |
| 2026-11-27 | `.venv\Scripts\python.exe -m pytest -q` | **red**: 6 failed, 189 passed | Все прежние тесты зелёные; падают только шесть новых контрактов |
| 2026-11-27 | `.venv\Scripts\python.exe -m mypy src`; `.venv\Scripts\python.exe -m ruff check .`; `.venv\Scripts\python.exe -m ruff format --check .` | pass | Type-only API компилируется строго; lint и format зелёные |
