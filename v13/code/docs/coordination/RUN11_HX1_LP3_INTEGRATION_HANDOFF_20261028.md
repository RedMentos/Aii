# V13 Run11 HX1/LP3 review integration handoff — 2026-10-28

## Exact source / authority

Branch `assistant/v13-hx1-lp3-merged-review-20261028`, draft PR #813; no production/main merge. Parent baseline PR #809 exact `4bd69282647d260efe815b6f57b72ed675fef588`, Actions 40610977438 SUCCESS (31 focused, 2105 full Linux software tests OK, 1 skipped, privacy CLEAN). Parent raw ZIP SHA256 `958d5d8d3c31d828af1592eae955793af9f20d0c524215a2b62cc3698b32969e`, CRC/internal SHA256 checked, private Library readback byte-identical.

Independent review PR #811 final `e2773e06075486ce8ed54c1fffec92f4200ec44c`: prereg `3a67c2811ef69c6d035c4b3d7799ff953ea88297`, RED Actions 40612374694 (20 focused, 3 FAIL), source fix `8eec0c293d3591063e96264e7c6ce0ba34d9e9b0`, final GREEN Actions 40612498319 SUCCESS (20 focused, 2108 full, 1 skipped, all exits0). RED ZIP SHA256 `ee2f3c7b759d87985e8ea77fed40693e1b872c3d484f424c2b46706619798e9d`, GREEN `429ed2b235144d47a2c6ad13b0dd37505f8b596990688fcbaddf4eead8a9a2e2`; both privately backed up with byte-identical readback. HX1 `_effective` now checks target/value against candidate-validated durable AG8-approved diff before serving SHADOW overrides. No live consumer.

Independent review PR #812 final `8aaa753558a4171f2e0e1da2712e58939d91b632`: prereg `cf3a6941ed4b594f2913d18635ea1312692ca54f`, RED Actions 40612721114 (18 focused, 6 FAIL), GREEN Actions 40612912886 SUCCESS (18 focused, 2108 full, 1 skipped, all exits0). RED ZIP SHA256 `ae886e0a0d19be81036c34dcf12c906f69593b7a96f917ad5b5f6067c4bf4cae`, GREEN `f50cd07aa2453867fda746475d773bba108d36ad449e0ecf6476c6c16e48a08c`; private Library readback byte-identical. LP3 shift control rejects mixed batches where any row receives its own prompt state after roll; source and frozen model weights otherwise unchanged.

Integration prereg `c5099d111a2292fab1a1ee3b1a772ca93c238d68` preceded exact two-parent merge `3e23f9b255d313a0524bf40d963fbe45e06d1bd5`, parents prereg HX1 descendant + LP3 head, tree `02d1478cf921a8cc04f0e56b18c101c6fe0699af`. Exact LP3 source/test/workflow/prereg blobs imported; HX1 source/test unchanged. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. Branch workflow commit `616ca803ed31b8036726b39fad99958fbf8e5518`.

## Acceptance and next command

Combined Actions **40613590051 in progress** at handoff writing; do not claim merged GREEN until its exact head `616ca803ed31b8036726b39fad99958fbf8e5518` passes focused/full/compile/privacy/diff and closed raw ZIP verification. After success, back up raw ZIP to private Library `/V13-Checkpoints/2026-10-28/Run11-HX1-LP3-Integration/`, materialize readback and compare SHA256, update PR #813. No auto-merge. No shared file owners overwritten.

On an environment with full source/dependencies: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_hx1_persisted_diff_binding_20261028 tests.test_lp3_shift_row_control_20261028 tests.test_hx1_revoked_applied_read_20261028 tests.test_lp3_state_prefix tests.test_f5_ag8_hx3_authority_isolation_20261028 tests.test_hx3_revoked_approval_read_20261028 tests.test_b3degrade tests.test_harness_hx`; then `PYTHONPATH=.:tests python -m unittest discover -s tests -p 'test_*.py' -q`. CI does this automatically without native models.

## Gates and open work

STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; LP3 heldout 0/12 new phrasing top1; jepa_weight=0; Age0/RECORD_ONLY; canonical_architecture_complete=false; user_full_scope_complete=false. Software/synthetic tests do not demonstrate native/Redmi model quality, real C3 language transfer, B1/B2 semantic complementarity or B3 receiver calibration. A1 PR #810 is separate and its full Linux Actions 40611249761 FAILED (SourceHandoff frozen Runtime guard; 2105 tests, 1 failure and 30 errors), so it is not integrated or called GREEN. Next substantive work: registered B1/B2 semantic complementarity and C3/B3 receiver prerequisites with original negative gates; investigate A1 frozen-source cohort conflict separately. Redmi device action remains unavailable in this runtime. Remaining execution budget UNKNOWN.
