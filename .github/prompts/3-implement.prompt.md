---
agent: agent
description: 'Step 3 — implement the approved memo until the suite is green. No scope beyond the memo.'
---

# Step 3 — Implement (GREEN)

## Preconditions

[STATUS.md](../../doc/work/STATUS.md) `stage` must be `tests` and the active
test plan must be `state: red`. Otherwise refuse and name the missing step.

## Do

1. Implement exactly what the memo describes, in the files it lists.
2. Run the full test suite, then the type check and linter named in the stack
   instruction files under [.github/instructions/](../instructions/). Fix until
   all are green.
3. Record every departure from the memo in its Deviations table, with a reason.
4. File anything discovered outside the memo's scope as a new backlog item. Do
   not tick it and do not implement it.
5. Update the test plan Run Record, `state: green`.
6. Update STATUS: `stage: implement`, `updated`. If blocked, `stage: blocked`
   and state the blocker in the memo.

## Never

- Exceed the memo's scope.
- Weaken, skip, delete or rewrite a test's expectation to make it pass.
- Break a hard rule in the Domain Risk section of
  [workflow.instructions.md](../instructions/workflow.instructions.md).

Finish with the handoff block from
[workflow.instructions.md](../instructions/workflow.instructions.md). Do not
continue into `/4-close`.
