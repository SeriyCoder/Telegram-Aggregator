# Test Plan — <ITEM-ID> <Title>

| Field | Value |
| --- | --- |
| item | <ITEM-ID> |
| memo | `doc/work/active/<ITEM-ID>-memo.md` |
| created | <YYYY-MM-DD> |
| state | red |

## Test Files

| Path | Runner | Covers |
| --- | --- | --- |

## Happy Path

-

## Privacy and Credential Safety (mandatory when tests.instructions.md requires it)

| Check | Test name |
| --- | --- |
| Unauthenticated clients cannot access private content | |
| Credentials/session material are absent from responses, exceptions and logs | |
| Session/configuration files are not web-served | |
| Simulated rate limits are respected without early retry or evasion | |
| Tests use no live network or real Telegram session | |

## Edge And Degenerate Cases

| Case | Test name |
| --- | --- |
| Empty input | |
| Single element | |
| All values equal | |
| Maximum realistic size | |
| No feasible solution | |

## Deliberately Not Tested

| What | Why |
| --- | --- |

## Run Record

| Date | Command | Result | Notes |
| --- | --- | --- | --- |
