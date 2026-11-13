# Telegram Knowledge Base — Project Brief

## Start Here

1. Read [STATUS.md](../doc/work/STATUS.md).
2. If `active_memo` is set, read that memo.

## What This Is

Локальная персональная база знаний для публикаций из выбранных пользователем
Telegram-каналов: сбор, простая фильтрация, поиск и закладки через
адаптивный веб-интерфейс. Это не бот для публикаций, не сервис массового
скрейпинга и не облачный продукт. Локальная основа MVP-01 создана; MVP-02
реализует импорт публикаций каналов из официального JSON-экспорта Telegram
Desktop (команда `import`), а прямой API-доступ остаётся заблокированным —
он требует поддержки спонсированных сообщений и вынесен в отдельный будущий
пункт. Веб-интерфейс ещё не реализован.

## Repository Map

| Path | Read this when… |
| --- | --- |
| `README.md` | You need installation, local run or validation commands |
| `doc/spec/telegram-knowledge-base.md` | You need required behaviour or acceptance checks |
| `doc/backlog.md` | You need the next item or want to file a new one |
| `doc/work/STATUS.md` | You need the current item and stage |
| `doc/work/README.md` | You need the loop, file naming or lifecycle |
| `doc/work/templates/` | You are writing a memo, test plan or audit |
| `doc/work/active/` | You are continuing the item in flight |
| `doc/work/archive/` | You need the reasoning behind a closed item |
| `doc/work/audits/` | You need past drift findings |
| `.github/prompts/` | You are running a loop step — the step definitions |
| `.github/skills/` | A step command must appear in a chat that lists skills |
| `.github/instructions/` | You need path-scoped rules |
| `src/telegram_knowledge_base/` | You are changing application layers: domain, use cases, adapters or web |
| `src/telegram_knowledge_base/web/templates/` (planned) | You are changing server-rendered pages or fragments |
| `tests/` | You are adding offline unit or integration tests |
| `data/` (planned, local runtime data) | You are handling the local database or other persistent user data |

## The Loop

| Step | Command |
| --- | --- |
| Memo | `/1-memo <ID>` |
| Tests (red) | `/2-tests` |
| Implement (green) | `/3-implement` |
| Close | `/4-close` |
| Audit | `/5-audit` |

## Non-Negotiable

1. **Privacy and Credential Safety** — Telegram credentials, session material and collected content stay local and are never exposed to unauthenticated clients.
2. Collection is read-only; do not send messages, automate channel discovery or bypass Telegram access and rate limits.
3. Keep Telegram, filtering, storage and web delivery in separate layers; web handlers never receive the Telegram session.
4. Network-dependent tests are forbidden; replace external services with test adapters.
5. The MVP is LAN-only. Do not add a tunnel provider or public deployment without a separate approved backlog item.
6. The current entry point is local-only and does not start an HTTP server. Add authentication before any route that can reveal private content.

## Environment

PowerShell 5.1: chain with `;`, never `&&`. Git belongs to the user — never run
it; suggest commands as text.
