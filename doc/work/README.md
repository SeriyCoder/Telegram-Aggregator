# Working Folder

The step loop turns one backlog item at a time into a reviewed, tested and
documented change.

```
idle --/1-memo--> memo --/2-tests--> tests --/3-implement--> implement --/4-close--> idle
                                                                  |
                                                                  v
                                                               blocked
```

`/5-audit` runs at any stage and leaves the stage unchanged.

## Files

| Path | Lifecycle |
| --- | --- |
| `STATUS.md` | Rewritten by every step; field names are fixed |
| `active/<ID>-memo.md` | Created by `/1-memo`; `status: draft` until the user approves |
| `active/<ID>-test-plan.md` | Created by `/2-tests`; `state: red`, then `green` |
| `archive/phase-<N>/` | Memo and plan moved here by `/4-close` |
| `audits/<YYYY-MM-DD>-audit.md` | One per `/5-audit` |
| `templates/` | Copied, never filled in place |

Memo approval is a human gate: answer the open questions, or reply "approved"
to accept the recommendations, before `/2-tests` will run.
