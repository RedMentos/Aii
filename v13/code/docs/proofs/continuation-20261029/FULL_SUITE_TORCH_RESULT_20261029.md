# Full cross-organ Linux software suite with pinned CPU torch — RED result (2026-10-29)

## Source and dependencies
- Review-only child of PR #1148 at `4f85688c2be9f0680db67f909a2c0815ba09829d`, exact workflow HEAD `12c3c152a5a183f7dd3899761a62d964854f0a97`. No runtime/Canon/registered cohort/model/seed changes.
- Isolated Ubuntu 24.04 Python3.12 venv; `numpy==2.2.6`, `torch==2.5.1+cpu` from official PyTorch CPU index. TORCH_IMPORT exit0, version `2.5.1+cpu`, CUDA False. PIP_CHECK exit0.

## Original unfiltered result
- Actions `40957012351`: **3285 tests, 0 FAIL, 6 ERROR, 11 skipped**, full suite exit1. This is a RED result; no waiver.
- Error categories: one `test_body_jepa.test_wide_and_tall` import `peft` missing; three imports of `transformers` missing in Body-JEPA checkpoint/LP3 tests; two frozen Run34/Run37 `native_source_or_catalog_changed` source/model pin errors. Earlier World-JEPA synthetic provenance regressions (27 invalid record count + 8 missing events) no longer appear after PR #1148 fixture repair. New tests and torch-enabled tests increase total from prior 3266 to 3285.
- Raw ZIP SHA256 `c3abbd38acc66b12f4bb495849dd3faccbdca74e93286f6d4e3c6102e5dc826d`; CRC clean, 22/22 inner SHA256SUMS. CANON/VENV/DEPS/TORCH/PIP_CHECK/TORCH_IMPORT/COMPILE/PRIVACY/DIFF all exit0; FULL exit1. Original ZIP privately backed up and re-materialized byte-exact at `/V13-Checkpoints/2026-10-29/Run10-FullSuiteTorch/`.
- Frozen Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## Negative gates and next
- Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; Redmi UNMEASURED; V13 INCOMPLETE. A software suite with only dependency/pin errors still does not prove native/causal/whole-system utility.
- Next command: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py'` in a fresh isolated venv with pinned compatible `torch`, `transformers` and `peft`. Do not change registered Run34/Run37 pins or suppress those tests to claim full PASS. Preserve original raw and exact new dependency versions.
