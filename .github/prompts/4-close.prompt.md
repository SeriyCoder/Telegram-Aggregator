---
agent: agent
description: 'Step 4 — gate on a green suite, tick the backlog, sync docs, archive the memo. Never runs git.'
---

# Step 4 — Close

## Preconditions

[STATUS.md](../../doc/work/STATUS.md) `stage` must be `implement`. Otherwise
refuse and name the missing step.

## Do

1. Re-run the full suite, type check and linter. Anything red: stop, set
   `stage: blocked`, report. No approval overrides this gate.
2. Compare the memo's Files table with the files actually changed. Explain every
   difference in Deviations.
3. Tick the item in [backlog.md](../../doc/backlog.md). This is the only step
   allowed to tick a box.
4. Sync documentation from the code: the
   [specification](../../doc/spec/telegram-knowledge-base.md) where behaviour was clarified, the
   [project brief](../copilot-instructions.md) repository map where folders
   were added.
5. If the item made a lasting design decision, propose an ADR under `doc/adr/`
   in the handoff; write it only on approval.
6. Move the memo and test plan to `doc/work/archive/phase-<N>/`.
7. Reset STATUS: `current_item: —`, `stage: idle`, `active_memo: —`, `updated`;
   append a row to the Closed Items Log.
8. Print a suggested commit message as plain text.

## Never

- Run any git command.
- Close with a red or unrun suite.

Finish with the handoff block from
[workflow.instructions.md](../instructions/workflow.instructions.md), naming the
next unticked backlog item. Do not start `/1-memo`.
