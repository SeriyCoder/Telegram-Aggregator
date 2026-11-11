---
agent: agent
description: 'Step 1 — write a design memo for one backlog item. No code, no tests.'
argument-hint: '<ITEM-ID>, e.g. M1-01'
---

# Step 1 — Memo

Item: `${input:item:Backlog item ID, e.g. M1-01}`

## Preconditions

1. Read [STATUS.md](../../doc/work/STATUS.md). `stage` must be `idle`. Otherwise
   refuse: name the current item and stage and the step that must finish first.
2. Find the item in [backlog.md](../../doc/backlog.md). If it does not exist or
   is already ticked, refuse.

## Do

1. Read the [specification](../../doc/spec/telegram-knowledge-base.md) sections the item references,
   the [project brief](../copilot-instructions.md) and any existing code the
   item touches.
2. Copy [memo.template.md](../../doc/work/templates/memo.template.md) to
   `doc/work/active/<ITEM-ID>-memo.md` and fill every section. `status: draft`.
3. The **Privacy and Credential Safety** section is mandatory and specific to the item. "Not
   affected" needs a one-sentence reason.
4. List every file expected to change. Put at least two entries in *Out of
   scope*.
5. End the memo with numbered Open Questions, each with a recommended answer.
6. Update STATUS: `current_item`, `stage: memo`, `active_memo`, `updated`.

## Never

- Write code, pseudo-code blocks or tests. Prose, tables and paths only.
- Edit anything outside `doc/work/`.

Finish with the handoff block from
[workflow.instructions.md](../instructions/workflow.instructions.md). Do not
continue into `/2-tests`.
