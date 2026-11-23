# JEF operator human outcome FINAL barrier — preregistration 2026-10-30

Base: PR #1168, verified checkpoint `44ccc360a1ddd0cb6168b6e7deb945b404392995`. Independent review-only implementation sibling to full-suite CI PR #1169; only this branch changes JEF runtime behavior. Ownership: `v13/code/v13/jefbridge.py`, JEF test files, new workflow, prereg and delta. No frozen native model, source, seed or cohort edits.

## Problem
`:note` / `inputs.record_rating` already require an assistant message with `status='FINAL'` before human learning. The separate explicit `:jef outcome` path currently only checks current session and numeric rating; it can update JEF shadow weights for a current-session event with no delivered FINAL answer. Canon W6 forbids learning from provisional state.

## Predeclared invariant
An explicit JEF operator outcome must be refused unless the referenced event belongs to the current session **and** has a persisted assistant FINAL message for that same session/event. A DRAFT/STREAMING/OUTPUT_COMMITTED/CANCELLED/DEADLINE/ERROR/INTERRUPTED or absent assistant answer is not a FINAL. The refusal occurs before JEFBridge.outcome and state write. Existing automatic `on_rating` already has the FINAL check and remains untouched. Do not grant any new authority.

## Checks
- Current session with JEFBridgeTurn but no FINAL: operator refuses; weights, receipts, updates unchanged. Also refuse a stored non-FINAL assistant message.
- Current session with an assistant FINAL and selected offer: operator rating works and identical repeated rating stays exact-once (PR #1168).
- A foreign-session FINAL still cannot be rated by the current session.
- Update existing synthetic operator fixtures to persist FINAL only in the positive cases; preserve their foreign-session/invalid-number controls.
- Run focused `test_jefbridge`, `test_jef_operator_session_20261030`, `test_jef_feedback_dedupe_20261030`, new FINAL tests and `test_inputs` where available; Canon/privacy/diff/compile, closed raw SHA256SUMS.
- Software only, Age0 RECORD_ONLY, no native/Redmi or STEP2/B3/Body-JEPA/LP3 promotion.
