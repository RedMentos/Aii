# P2X scale0/1 training-only handoff — 2026-10-29

## Exact lineage and ownership
- Parent: PR #1106 head `c16c5f71ee9cebd50bc07330d6cc45245de7460b` (later parent source CI dependency fix does not alter inherited C3 source); child PR #1107, review-only. Production main remains older.
- Prereg `f9bead350a59bdfafe3bc096c7a24c4a0db35283` committed before script/tests/workflows. Branch owns only `docs/coordination/P2X_SCALE01_TRAIN16_PREREG_20261029.md`, `scripts/p2x_scale01_train16.py`, `tests/test_p2x_scale01_train16_20261029.py`, its two workflows and this handoff. No donor source edited, no forced push.
- Frozen training16 source and adapter/model/runtime SHA256 remain exactly as prereg. 16 balanced training examples × LoRA scale0 and scale1, same JSON schema, no heldout/CAL36 rows, no weights updated, no live authority.

## Original RED and fix
- Original native Actions `40898786616` exact head `4bf374b1e3c6f3d3ef9ac93a6ec5a61390ee99c5` stopped before installation/native: focused test 20/21 PASS, 1 ERROR. Cause: score's `per_label` map had integer keys 0/1; JSON persisted stringifies them, so independent `verify` rejected score replay. This is a real serialization defect, not native model failure.
- Original RED artifact `12909020530`, ZIP SHA256 `d7ad7e16eaf9bd20059c64e0594c01e4cb628a93f6bc38f6b629c9f89d901e8`, CRC clean, preserved privately `/V13-Checkpoints/2026-10-29/P2X_SCALE01_NATIVE_ORIGINAL_RED_40898786616_SHAd7ad7e16.zip`. Do not discard or relabel.
- Fix `0f5f088162e00008f372fda2a1bfdc47ede592d3` serializes `per_label` with string keys; regression `367c5acb371f61c2529cb20a503f52a3797c44c5` asserts JSON round-trip identity. Native workflow repinned to new script blob `f60afc69f5a6b88a40f76c26c03df74acfbe54b5` and test blob `6d268508b15b2b7abcca73f2fdf8b71f99e760e9`.
- Fresh native Actions `40899022720` on `addd8c819411c7055c57012fa91772eeb8314219` launched; source-only focused/full Actions `40899042923` on `7ba517f5d0d61923e99fcb95dfed74f458843682` launched. Outcomes **pending** at this checkpoint; never call GREEN without exact raw verification. Prior source full runs may be RED because CPU torch was missing; current source workflow installs pinned `torch==2.14.1` from official CPU wheel index.

## Next exact commands
1. Fetch current runs `40899022720` and `40899042923`, inspect all stage exits, raw ZIP CRC/SHA256SUMS and head SHA. For focused: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_p2x_scale01_train16_20261029 tests.test_p2x_schema_toggle_train16_20261029 tests.test_p2x_json_train16_eval_20261029`.
2. Native: independently replay `python -m scripts.p2x_scale01_train16 --verify <evidence>` with exact-head source, compare all 16 paired requests/launch flags and correct strict actions. Preserve negative outcomes, even if all NONE. Separate native success from actual model quality.
3. If no observed scale effect, do not infer zero weight effect; preregister a bounded first-token probability/logit or adapter-application diagnostic, still on training-only cohort, or pursue other canonical packages. No frozen heldout tuning.
4. Private backup and byte reverify raw, update BUILD_STATE/handoff/review PR, continue useful independent work.

## Negative gates
Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; Redmi unmeasured; V13 incomplete.
