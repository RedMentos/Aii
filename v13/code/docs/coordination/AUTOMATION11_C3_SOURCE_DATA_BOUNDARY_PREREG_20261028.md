# C3 source consumer data-boundary candidate — preregistration, 2026-10-28

**Owner**: independent GPT-6 software implementation. **Base**: #879 at `8716373b62e1f873129993ba09eb84ad242ac0be`, distinct review branch; no mutation of #879 or historical #876 RED. Prior guarded native source-consumer #879 `40657402696` was scoped PASS 8/8 positive, 24/24 deterministic negative; verified independently in #882. This new candidate has **no new native result**.

## Threat and scope

Existing `source_consumer.admit` checks SourceRef, session, topic and conflicting corrections, but accepts **arbitrary verified source text** as a budget value. `render_messages` interpolates `source['topic']` and `source['value']` unquoted into a high-priority system message. A user-provided value such as `615 Euro\nIgnore previous instructions` is source-authentic but **not a safe budget datum**; provenance does not grant instruction authority. In addition, `render_messages` is a prompt renderer and does not independently verify an untrusted caller's admission dictionary.

## Candidate and acceptance

- Keep the existing source-consumer module **not wired to Runtime**. Preserve `v13/runtime.py` exact Git blob `68e7ed1352800174972558f1e0b0683a42c8689a`; no new C3, B, JEPA, Age, tool or policy authority.
- Validate a bounded **ASCII integer 1–9 digits + explicit Euro/EUR/€** source value and a simple `Project|Projekt NAME budget|budgets|etat|finanzrahmen` topic **before** admission or prompt interpolation. Reject embedded instructions, newline, extra numbers, currency ambiguity, topic injection and empty/non-string data with deterministic CLARIFY/no model. Conservative rejection of grouped/decimal amounts is deliberate until a separate locale cohort; no false numerical acceptance.
- Keep existing frozen `render_messages(cfg,query,admission)` API for #879 evidence, but guard topic/query/value again at rendering and reject malformed or cross-topic source dictionaries. This is a defense-in-depth renderer, **not** an authority validator for arbitrary Python callers. Future Runtime wiring must call a new trusted admission+render wrapper (or reverify SourceRef itself); do not describe a forged dictionary as verified evidence.
- Add separate tests (no rewriting frozen tests) for original 615 Euro positive, malformed budget strings, conflicting and wrong project, newline/topic prompt injection, missing values, unsupported query, and renderer rejection. Explicitly verify zero model invocation for refused cases in software.
- Run focused old+new tests and entire 2274+ software suite in isolated pinned CI; preserve failures and raw artifacts. Source/model/seed of #879 remains historical; any new native result requires its own preregistration and model hash verification. No Redmi or native claim from this candidate.
- Preserve all original negative gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA unavailable, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY, Redmi unmeasured.

**Next command after prereg**: implement source value/topic boundary and new tests; verify remote blobs; run independent full-suite GitHub Actions on this branch. If full suite RED, keep review-only and pursue another independent canonical package rather than hiding errors.
