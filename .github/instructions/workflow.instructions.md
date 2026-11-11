---
applyTo: '**'
description: 'Telegram Knowledge Base working contour: STATUS first, step loop, domain risk, handoff format.'
---

# Workflow

## Start

Read [STATUS.md](../../doc/work/STATUS.md) before answering anything about
project state or next steps, then the active memo if one exists.

## The Loop

| Step | Command | Requires stage | Sets stage | Never |
| --- | --- | --- | --- | --- |
| 1 | `/1-memo <ID>` | `idle` | `memo` | Writes code or tests |
| 2 | `/2-tests` | `memo`, memo approved | `tests` | Writes production code |
| 3 | `/3-implement` | `tests` | `implement` / `blocked` | Exceeds the memo, weakens a test |
| 4 | `/4-close` | `implement`, suite green | `idle` | Runs git |
| 5 | `/5-audit` | any | unchanged | Changes source code |

One item at a time. Scope creep becomes a backlog item, never a silent addition.

Use the loop for changes to collection, filtering, persistence/schema, search,
authentication, network exposure, secret handling, backups or external
integrations. Direct edits are limited to copy, translation strings and
presentation-only styling that do not alter access, data or behavior.

## Domain Risk — Hard Rule

**Privacy and Credential Safety.**

- Risk enforcement belongs at configuration, Telegram-adapter, storage,
  authentication and logging boundaries; templates and browser code never
  receive Telegram credentials or session objects.
- Every route that can reveal private content requires authentication; tests
  verify unauthenticated requests cannot read it.
- Keep session files and secrets outside tracked source and redact them from
  logs, errors and rendered responses.
- The MVP listens only on the configured LAN interface; no tunnel or public
  endpoint is enabled by default.
- Respect Telegram-provided wait periods. Never evade a limit by rotating IPs,
  restarting sessions or issuing concurrent retries.

A change that weakens any of these is rejected regardless of approval.

## Handoff Block

Every step ends its reply with these five parts, written for someone who has
not read the prompt:

1. **Status** — `was → now`, and what that means.
2. **What happened** — one or two plain sentences.
3. **Where it lives** — links to every artifact touched.
4. **What I need from you** — numbered decisions, each with a recommendation.
5. **Next** — the exact next command and what it does.

If a bare "approved" is not a complete answer, the recommendations are missing.

## Approval Rule

"approved" means: apply every recommendation, record it in the artifact (not
only in chat), advance the stage, and run **exactly one** next step, then hand
off again. A partial approval is not an approval. No approval overrides a gate:
a red suite, missing privacy and credential safety tests, or an unapproved memo.

## Contour Files

These files are the process itself:

- `.github/prompts/<N>-<step>.prompt.md` — the step logic, defined once
- `.github/skills/<N>-<step>/SKILL.md` — thin `/` entry points for chats that
  list skills rather than prompt files; they only point at the prompts and must
  never restate step logic
- `.github/instructions/*.instructions.md`
- `.github/copilot-instructions.md`
- `doc/work/README.md`, `doc/work/STATUS.md` field names
- `doc/work/templates/*.md`

Edit them **directly** — no memo, no tests, no close step. Record each edit as a
`CONTOUR-*` backlog item; the next review verifies the contour still holds
together. A process cannot validate a change to itself.

## Conventions

- Never run git. Suggest commands as text.
- Shell: PowerShell 5.1 — chain with `;`, never `&&`.
- Working documents, memos, backlog and specs: Russian. Chat replies
  follow the user's language.
- Working documents live in `doc/work/`; the specification in `doc/spec/telegram-knowledge-base.md`.
