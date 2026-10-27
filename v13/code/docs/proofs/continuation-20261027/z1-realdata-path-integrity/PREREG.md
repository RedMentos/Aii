# WP-Z1 real_data evidence path integrity — preregistered review (2026-10-27)

Owner: GPT-6 automation11, independent child of PR #695 head `6e10df6dafc433e668b1f28a1092e4c88d104aa3` (itself child of five-parent PR #672). Baseline `v13/code/v13/gates.py` blob `942caafe1da0e0efcd6004ae5b21062c58fdf1c1`. This prereg is committed before changing source/tests.

Problem: `check(...)` accepts `real_data` merely when a path starts with `docs/proofs/`, `docs/canon/` or `../bench-results/` and `(APP/path).exists()`. An existing directory or a traversal/symlink resolving to unit tests can therefore satisfy the real-data criterion. This can incorrectly turn an unmeasured gate GREEN (or partially complete), independent of the strict verdict types fixed by PR #695.

Scoped fix: for the **real_data criterion only**, require a regular file whose *lexically normalized path* lies in one of the three existing allowed roots, and whose resolved path stays in that root; reject symlinks and path traversal. Preserve canonical `../bench-results/<file>`, `docs/proofs/<file>`, `docs/canon/<file>` paths and existing verdict semantics. Do not modify the registered gate graph, benchmarks, models, cohorts, hashes, authority, or other criteria. A path check is not proof of native execution or semantic validity; retain negative gates.

Prospective counterexamples: (1) directory masquerading as real data, (2) `docs/proofs/../../tests/` traversal, (3) `../bench-results/../code/tests/` traversal, (4) symlink file pointing at tests, (5) symlinked parent directory pointing at tests, (6) absolute/non-string/missing paths, (7) valid regular files under each existing allowed root, (8) existing graph statuses and explicit negative verdicts remain unchanged.

Acceptance: isolated tests exercise `check` and `evaluate` fail-closed cases; existing `test_register_gates` and `test_z1_gate_evidence_type` remain GREEN, `compileall` succeeds; source hygiene and privacy scan CLEAN. CI Actions are software-only. Historical broad suite remains RED unless separately closed with differential proof. No STEP2, B3, Body-JEPA, Redmi, or full V13 promotion.
