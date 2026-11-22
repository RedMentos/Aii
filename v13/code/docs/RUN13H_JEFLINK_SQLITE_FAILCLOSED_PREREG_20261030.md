# Run13H — JEF source-link SQLite failure containment (preregistered 2026-10-30)

Owner GPT-6. Child of G14 PR #1295 at `4c789ae85758ca71bf86dd5067ab697913071a51`; isolated review branch `assistant/v13-run13h-jeflink-sqlite-failclosed-20261030-auto11`. This document is committed **before** tests or implementation. Scope is only read-only, opt-in Age0 SHADOW diagnostics; no automatic C3 output, tools, learning, authority or model calls.

## Observed gap, not yet an executed failure

Code inspection at the pinned parent shows `Store.one -> Store.rows -> sqlite3.Connection.execute` can raise `sqlite3.Error`, while `v13/jef_context_link_operator_run13f.py::_last` and `v13/agi/context_source_link_budget_run13e.py::propose_pointer` do not catch this family. The explicit three-ID command also performs an uncaught `Store.one` query before entering the protected proposer. This can escape an operator diagnostic as a Python exception on malformed/closed SQLite state; a safe SHADOW diagnostic should return `SHADOW_NO_AUTHORITY` with no answer and no native call.

## Fixed test-first acceptance

1. Add focused unittest regressions using actual `Runtime` / `Operator` and fault injection only on `Store.one`: `:jeflink last`, explicit `:jeflink <packet> <query> <source>`, and `propose_pointer` all fail closed on `sqlite3.DatabaseError` and `sqlite3.OperationalError`. Confirm `answer=None`, `delivery_authority=0`, `native_calls=0`, `weight_updates=False`. An invalid explicit ID still raises `ValueError` before store access.
2. Run tests against parent source first; retain failing output (expected RED). Apply narrow exception normalization in the two read-only modules, not `Store` or the live Runtime. Rerun same tests, expect PASS. Run existing Run13E/F/G tests without filtering and `compileall`. Privacy scan and `git diff --check` must pass. Preserve all negative gates.
3. GitHub Actions focused workflow may execute the test-first RED and implementation GREEN in separate commits. Retain original logs, exit codes, SHA256SUMS and HEAD. Verify remote file bytes and PR head before claiming checkpoint. Full-suite G14 and original native RED remain independent; no inference from focused PASS.

Potential false positive: an intentionally invalid command must still raise before any DB read; no broad `except Exception`. No changes to frozen Canon, registered sources/models/seeds/scorers, or G14 original full-suite workflow. The G14 workflow's simultaneous `FULL_EXIT==0` and nonempty historical failure-identity match is an independent review note; do not reinterpret its RED as GREEN.
