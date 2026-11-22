# JEF explicit-human receipt integrity across self-outcome training — prereg 2026-10-30 run11d

Review-only owner `assistant/v13-jef-human-receipt-run11d-20261030`, parent #1225 HEAD `852f2c6ccef375cb03a0ad8318fec851f3b191ad`. File ownership for this package: `v13/jefoutcome.py`, `v13/learning.py`, new JEF receipt tests/workflow/scoped docs. No other owner branches overwritten. Canon v10.16.1 and all source/model/seed gates remain unchanged.

## Concrete defect hypothesis (before tests/fix)
`jefoutcome._human_label_exists` currently treats a feedback row plus a HumanDecision packet sharing a source_id as an authoritative human veto **without** requiring source kind `HUMAN_DECISION`, packet value/permission/hash matching feedback/source, or the decision's event binding. Separately, `learning.shadow_readout` builds `human_keys` from similarly weak HumanDecision packet linkage. A stale or substituted receipt may suppress otherwise valid JEF self-outcome rows even though no valid explicit human correction exists. Conversely a valid human RECORD must always outrank a self-label, even if old/outside recent windows.

## Frozen test plan
- Commit focused real-Store regression tests **before** implementation. Expected baseline RED for forged/mutated human receipt (feedback value, packet value, source kind, source-ref hash, decision/event mismatch) while valid RECORD veto and revoked-source behavior remain intact. Preserve original RED Actions raw.
- Add one shared exact human receipt predicate in JEF outcome code; require matching feedback/packet/decision event, component, value, permission, source ID/hash/span, source kind and live byte-verified source text. Use in both JEF `training_rows` veto and `learning.shadow_readout` human-key selection. No change to actual human feedback write path, label classes, optimizer thresholds or mode defaults.
- After fix run focused new tests + existing JEF self-source/human-record/report tests and full-suite independent review. All native/Redmi claims remain unavailable. This is a provenance/learning admission integrity repair, not permission to learn at Age0.
- Require fail-closed handling for malformed or deleted receipts, and preserve the valid human RECORD precedence (including older >512 feedback) with no fabricated self labels. No approval, age or gate promotion.

Gates: Age0 RECORD_ONLY; JEF outcome default record; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA unavailable; jepa_weight=0; Redmi UNMEASURED; whole V13 incomplete. Next command after tests: `cd v13/code && PYTHONPATH=.:tests:scripts python3 -m unittest -v tests.test_jef_human_receipt_integrity_20261030`.
