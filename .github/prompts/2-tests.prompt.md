---
agent: agent
description: 'Step 2 — write the test plan and real failing tests for the approved memo. No production code.'
---

# Step 2 — Tests (RED)

## Preconditions

1. [STATUS.md](../../doc/work/STATUS.md) `stage` must be `memo`.
2. The active memo must have `status: approved`. On `draft`, refuse and list the
   unanswered open questions.

## Do

1. Copy [test-plan.template.md](../../doc/work/templates/test-plan.template.md)
   to `doc/work/active/<ITEM-ID>-test-plan.md` and fill it.
2. Include the mandatory **Privacy and Credential Safety** category from
   [tests.instructions.md](../instructions/tests.instructions.md) whenever the
   item touches the paths that file names.
3. Write real tests in the paths the memo names. Minimal stubs or type-only
   exports are allowed so the suite compiles; no behaviour.
4. Run the suite. Confirm the new tests fail for the intended reason, not because
   of syntax or missing tooling. Record the run in the plan, `state: red`.
5. Update STATUS: `stage: tests`, `updated`.

If the toolchain does not exist yet and this item creates it, the RED evidence is
the missing or failing test command itself; record exactly what failed.

## Never

- Implement behaviour to make a test pass.
- Weaken, skip or delete a test.

Finish with the handoff block from
[workflow.instructions.md](../instructions/workflow.instructions.md). Do not
continue into `/3-implement`.
