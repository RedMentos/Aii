# Run127 — independent STEP2 matched-C3 raw verifier preregistration (2026-10-29)

## Frozen parent and scope
Review-only child of PR #1026, exact parent commit `7f25f3b0d0d8b7167817420240d0475f57f0a538`. This registration is committed **before** the new auditor and tests. It does not authorize native inference, merge, model changes or canonical gate promotion. Original Run116 source report SHA256 `c0cd539ec28f9583abe25c93f48871597df6758c442782eb6fedd56ad612105f`; frozen six-fixture SHA256 `b8896bfba0c6c323ba1dafd12bc788e7f378bbf5d23c96e5074b3b1d058ef1d1`. Original model B1/B2/C3 hashes, CQP body seed20 and C3 seed13 unchanged.

## Problem and acceptance
The staged Run126 executor records 84 C3 rows and a receipt, but an independently executable **read-only** verifier is needed before any result can be accepted. Implement isolated `scripts/step2_exact_rule_transport_verify.py` and synthetic `tests/test_step2_exact_rule_transport_verify.py`. It must verify exact original source/preflight, unique complete 42 matched pairs, all 84 FINAL rows, alternating execution order, model and runner provenance before/after, source/message/row hashes, oracle-hidden flag, per-row tool replay and exact scorer recomputation, receipt summary and full evidence SHA. Detect tampering, duplicate/omitted/reordered rows, changed action/score, incorrect PASS status, and incomplete raw. Fail closed and never rewrite original evidence. Emit independent per-fixture and per-variant matched deltas as a **diagnostic only**. Preserve original failure evidence and negative gates. No synthetic result may be presented as native evidence.

## Tests and stopping gates
First run self-contained synthetic red/green cases; then focused repository tests and full suite/privacy in a **software-only** GitHub Actions workflow if the parent exact-head software job and resource owner allow. Do not run the native model in this package. If the parent CI is pending, proceed with this independent software work; no native launch. A review-only PR and remotely verified commits are checkpoints, not a main merge.

Gates: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi UNMEASURED; whole system INCOMPLETE.
