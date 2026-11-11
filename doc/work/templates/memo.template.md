# Memo — <ITEM-ID> <Title>

| Field | Value |
| --- | --- |
| item | <ITEM-ID> |
| epic | <epic> |
| phase | <phase from STATUS> |
| status | draft |
| created | <YYYY-MM-DD> |
| closed | — |

<!-- No code anywhere in this memo: prose, tables and file paths only. -->

## Problem

One paragraph. If it needs two, the item is too big.

## Scope

**In scope**

-

**Out of scope** (at least two)

-
-

## Approach

How it will work, referencing specification sections.

**Rejected alternative:** one sentence and why.

## Data / Schema Delta

| Entity / field | Change | Version or migration impact |
| --- | --- | --- |

## Interface Delta

Public functions, UI surfaces, commands or file formats added or changed.

## Privacy and Credential Safety

| Question | Answer |
| --- | --- |
| Is any Telegram credential or session material introduced, moved or exposed? | |
| Can an unauthenticated client reach any content-bearing route or file? | |
| Does the change alter where local data or session files are stored? | |
| Could an error, log, template or response reveal secrets or private content? | |
| Does the change affect rate-limit handling or remote connectivity? | |
| How it is proven by tests | |

If not affected, say why in one sentence.

## Files

| Path | Change |
| --- | --- |

## Definition of Done

- [ ] Tests written first and seen red
- [ ] Mandatory privacy and credential safety tests present where applicable
- [ ] Suite, type check and lint green
- [ ] Domain Risk hard rules respected
- [ ] Spec and project brief synced
- [ ] Deviations recorded

## Open Questions

1. <Question> — **Recommendation:** <answer>

## Deviations

| Step | Deviation | Reason |
| --- | --- | --- |
