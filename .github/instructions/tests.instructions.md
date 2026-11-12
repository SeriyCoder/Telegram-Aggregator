---
applyTo: 'tests/**'
description: 'Test rules: red first, mandatory domain-risk category, no network.'
---

# Tests

Tests live under `tests/`, mirroring `src/telegram_knowledge_base/`; use the
toolchain and naming convention established by MVP-01. Unit and integration
tests use fakes for Telegram and never require credentials or network access.

- Tests are written in `/2-tests`, before implementation, and must fail first
  for the intended reason.
- Never weaken, skip or delete a test to make it pass. A wrong test is fixed in
  the open, with the reason recorded in the memo's Deviations.
- No network in any test.
- Test names state behaviour, not the function under test.

## Mandatory Category — Privacy and Credential Safety

Any change to `src/telegram_knowledge_base/config/`,
`src/telegram_knowledge_base/adapters/telegram/`,
`src/telegram_knowledge_base/adapters/storage/`,
`src/telegram_knowledge_base/web/`, authentication, logging or deployment
configuration must include the checks below wherever the corresponding
behavior exists. Record in the test plan why a check is inapplicable; do not
create a test-only implementation to make an absent boundary appear testable.

1. If private content can be served, unauthorized requests cannot read pages,
   search results or stored content. If no web server exists, test that the
   local entry point does not start one.
2. Credentials and session material do not appear in responses, exceptions or
   captured logs. Use synthetic values wherever the changed code can handle
   such material.
3. Session/configuration paths remain local. Where a web server exists, verify
   that these files are not served by static-file routes or templates.
4. For changes to Telegram request, rate-limit or retry behavior, including
   configuration that affects it, a simulated rate-limit response is respected;
   no early retry or evasion path is taken.
5. Tests make no live network calls and do not require a real Telegram session.

## Degenerate Cases

Always consider: empty input; single element; all values equal; maximum
realistic size; no feasible solution.

For maximum-size cases, exercise the configured per-run collection and page
limits established by MVP-01; record those limits in its memo rather than
assuming an unmeasured throughput target. No-feasible cases include an
unauthorized request, an unavailable Telegram source, no matching posts, and
an unavailable FTS5 capability.
