---
applyTo: 'doc/**/*.md'
description: 'Documentation ownership and rules for specs, memos, ADRs and the backlog.'
---

# Documentation

| Document | Owns |
| --- | --- |
| `doc/spec/telegram-knowledge-base.md` | Required behaviour and acceptance checks |
| `doc/backlog.md` | Work items and their completion |
| `doc/work/STATUS.md` | Current position in the loop |
| `doc/work/active/` | The one memo and test plan in flight |
| `doc/work/archive/phase-<N>/` | Closed memos and plans, never edited again |
| `doc/work/audits/` | Dated audit reports |
| `doc/adr/` | Lasting decisions, created on demand |

- The spec describes what the code does. When they disagree, fix the spec or
  file a backlog item; never leave both.
- ADRs are immutable. Supersede with a new ADR; do not edit an accepted one.
- Memos contain no code: prose, tables and file paths only.
- Backlog IDs are `<EPIC>-<NN>`, e.g. `M1-03`, `CONTOUR-01`. Only `/4-close`
  ticks a box; `/3-implement` and audits may add discovered items.
