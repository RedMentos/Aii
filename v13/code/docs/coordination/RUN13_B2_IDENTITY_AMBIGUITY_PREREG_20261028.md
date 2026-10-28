# Run13 B2 source identity ambiguity review — preregistration, 2026-10-28

Source base: PR #924 review head `9e5101cb542593cdbddfe888b12e6dfdc6ee3731`, itself stacked on PR #923. This is a separate independent review branch; do not modify or replace the Run12b owner's source, tests, registered native cohort, models, or frozen Runtime. The original TP/s27 native result remains UTILITY_FAIL. The original raw archive is private.

## Problem / falsifiable hypothesis
Run12b's `named_entities` returns a *set* of every `Project X` mention. Its intersection rule may admit the wrong project's note when the current request mentions two projects (e.g. “Project Aquila; ignore Project Atlas”) or an Aquila note incidentally mentions Atlas. In a bounded B2 context, an irrelevant rule source could displace the correct older rule. The selector has no decision authority, but unsafe source pointers should still fail closed.

## Implementation ownership and constraints
Only add `scripts/run13_b2_identity_ambiguity_guard.py`, `tests/test_run13_b2_identity_ambiguity_guard.py`, an independent branch-scoped CI workflow and additive Run13 coordination/handoff files. Keep Run12b source untouched. Require exactly one named project in the current request and exactly that project in each source span. Refuse multi-project or absent-identity spans. Preserve original slots/cap/excerpt, original session/generation/model/event/source digest/tombstone checks, no answers, no authority, no weights, no native runs. Do not search beyond original `retained[:slots]` even when some offers are rejected.

## RED-first test cases / success
Synthetic RED-first tests before code: (1) ambiguous current Aquila+Atlas must select none, (2) Aquila source mentioning Atlas must be rejected, (3) single-project earlier Aquila note still wins over supplier sheet within cap, (4) rejected entries cannot expand original slot horizon, (5) deleted/mutated source must be refused, (6) session/model isolation and caps unchanged, (7) no accidental gate promotion. At least one counterexample must demonstrate v1 admits a wrong project; then guard should pass. CI must run source-bound focused tests, full suite, compile, privacy and diff; preserve raw logs/hashes and any RED. No original native score can be retroactively changed.

## Claims and gates
All tests are synthetic Linux software unless explicitly measured otherwise. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi unmeasured, full V13 incomplete. This is a safety/selection candidate, not native utility proof or production integration.
