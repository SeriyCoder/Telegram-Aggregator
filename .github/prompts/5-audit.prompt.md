---
agent: agent
description: 'Step 5 — audit backlog, docs, working folder and domain-risk coverage for drift. Never changes source code.'
---

# Step 5 — Audit

Runs at any stage and does not change `stage`.

## Do

1. Copy [audit.template.md](../../doc/work/templates/audit.template.md) to
   `doc/work/audits/<YYYY-MM-DD>-audit.md` and fill every section.
2. Check the contour files listed in
   [workflow.instructions.md](../instructions/workflow.instructions.md) still
   agree with each other and with the STATUS field names. Each
   `.github/skills/<step>/SKILL.md` must only point at its prompt.
3. Check privacy and credential safety coverage: every path named in
   [tests.instructions.md](../instructions/tests.instructions.md) has the
   mandatory test category, and no hard rule of the Domain Risk section is
   broken.
4. Fix documentation drift directly. Record each fix under Actions Taken.
5. File one backlog item per HIGH finding.
6. Set `last_audit` and `updated` in [STATUS.md](../../doc/work/STATUS.md).

## Never

- Change source code or tests.
- Leave a HIGH finding only in the report.

Finish with the handoff block from
[workflow.instructions.md](../instructions/workflow.instructions.md).
