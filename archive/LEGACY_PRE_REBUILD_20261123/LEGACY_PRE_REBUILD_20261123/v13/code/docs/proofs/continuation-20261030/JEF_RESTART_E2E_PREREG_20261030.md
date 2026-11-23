# JEF FINAL/outcome restart and delivered-turn integration — preregistration 2026-10-30

Base: PR #1170, verified checkpoint `b7fcf04a7dd2becc166cb7f418896de83baf0dfb`. Review-only test/evidence child. Ownership: new `test_jef_restart_e2e_20261030.py`, CI workflow, prereg/delta only. No runtime, Canon, model or registered cohort edits.

## Functional objective
Show that the newly guarded explicit JEF outcome path is usable after a real delivered Runtime FINAL (with a stub C3 model, not a native claim), and that duplicate human SGD receipts survive an actual SQLite close/reopen. On restart the old event must not become accessible through a new session's `:jef last/outcome`.

## Predeclared checks
1. Real Runtime.submit → output governor persists assistant FINAL; JEFBridgeTurn is visible via `:jef last` only in that session. Explicit `:jef outcome` on that FINAL is accepted (zero selected B offers means zero weight updates). No native model download.
2. Build one selected-offer synthetic JEF turn with a persisted FINAL and a human rating. Close Runtime, reopen same home, verify JEF state and receipt persisted; direct repeated `JEFBridge.outcome` has zero extra SGD; the new session's operator refuses the old event.
3. Run the new tests plus all previous JEF operator, dedupe, FINAL, bridge and inputs focused tests. Preserve Canon, privacy, diff, compile and closed raw SHA256SUMS.
4. No gate promotion: software only, Age0 RECORD_ONLY, jepa_weight=0, STEP2/B3/Body-JEPA/LP3/World-JEPA/Redmi still open.

## Next
Integrate sibling full-suite review evidence (PR #1169) with the latest FINAL/restart branch; rerun unfiltered full corpus after all JEF changes, preserving historical Run34/Run37 failures.
