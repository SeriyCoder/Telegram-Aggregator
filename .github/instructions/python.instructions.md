---
applyTo: '**/*.py'
description: 'Python layering, forbidden patterns and check commands.'
---

# Python

## Layering

| Path | Contains | May import |
| --- | --- | --- |
| `src/telegram_knowledge_base/config/` | Local settings and secret-path validation | Standard library; never web templates |
| `src/telegram_knowledge_base/domain/` | Pure filtering and domain rules | Standard library only |
| `src/telegram_knowledge_base/application/` | Use cases and ports | Domain |
| `src/telegram_knowledge_base/adapters/telegram/` | Telethon client and ingestion boundary | Application, domain and Telethon |
| `src/telegram_knowledge_base/adapters/storage/` | SQLite schema, transactions and FTS5 | Application, domain and SQLite |
| `src/telegram_knowledge_base/web/` | FastAPI routes, authentication and templates | Application and web framework; never Telegram session objects |
| `tests/` | Offline tests mirroring the source layers | Project code and test dependencies |

Privacy-critical checks live at configuration, Telegram-session, storage,
authentication, network-binding and logging boundaries.

## Forbidden

- Never hardcode credentials, commit session material, or log secrets/message
  contents.
- Never call blocking Telegram or database work directly on the async event
  loop; use the chosen async-safe adapter pattern.
- Never expose the Telegram client/session to route handlers or templates.
- Never send messages, evade rate limits, or add unbounded retry loops.
- Do not add live-network tests or arbitrary regular-expression filters in the
  MVP.

## Checks

The toolchain does not exist yet. MVP-01 creates the Python project metadata,
test runner, type checker, linter and formatter, then records their exact
commands here before implementation begins.
