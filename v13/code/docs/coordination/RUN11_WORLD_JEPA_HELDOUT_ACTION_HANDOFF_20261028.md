# Run11 World-JEPA heldout-action fixed-readout SHADOW checkpoint — 2026-10-28

**Review-only; not production.** Parent #826 exact `0cc5e59fc1c91a71b0b232b42f70668c562d9d2b`. Owner GPT-6, only new isolated research script/test/workflow/docs. Prereg `adbe07da8191d4bf161740a69f1548ddd67e0794` preceded source `99c376354c84cdb3501c8cc2dd040265400e8a16`, tests `952052260de1569774c861364a3e40b300d170d8` and CI `f2e2bea2c8982caaf22d022538296ee0ee736c56`. Original World-JEPA, registered cohorts, frozen Runtime and Canon unchanged.

## Research question and measured result

Old wrong-action controls fit ridge readout on wrong-action features **in both train and heldout**; the ridge can relearn the wrong-action mapping. This new separate ablation trains World-JEPA and fits **one** outcome readout on correct training actions, freezes its weights, then changes actions on heldout only (row shift preserving heldout marginals, or action-column rotation). Fixed original seeds 3/7, ensemble 3, 400 training steps, 64 synthetic digital outcomes (47 train/17 heldout), deterministic fixture seed 20261027. No private observations or native models.

GitHub Actions `40624788398` at exact `f2e2bea2c8982caaf22d022538296ee0ee736c56`: **9/9 focused tests PASS** (including original row-permutation controls), NumPy install, actual 400-step synthetic run, report validation, compile, privacy CLEAN and diff all exit 0. Raw ZIP artifact `12788856919` SHA256 `0f7a2824369ff50f5929e3d1cd6bdacb35ff211f66bd03bfd0eeed22902cde5e`; CRC and internal SHA256 verified. Source Git blob `7d23ae54866fc3b061265a40ae4c1a7cd0ab30b0`.

Pooled MAE (lower better): **direct scaled ridge 0.152580**. World-JEPA correct-action fixed readout: **seed 3 = 0.244031**, **seed 7 = 0.214771** (both *worse* than direct by 0.091451 and 0.062191 respectively). Heldout row-mismatched actions: 0.489604 / 0.273740; column-mismatched: 0.469246 / 0.261331. Both mismatches changed 100% of heldout rows, with row-action marginals preserved. Thus there is **action sensitivity but no attributable predictive utility beyond the direct baseline on this synthetic fixture**. Do not promote any learning gate.

Private persistent Library backup `/V13-Checkpoints/2026-10-28/Run11-World-JEPA-Heldout-Action/GREEN-40624788398.zip` re-materialized byte-exact (SHA256 above). No model weights or private identifiers uploaded to public Git.

## Scope, blockers and next command

Scope is observed-digital/synthetic SHADOW, not real-world action causality. `runtime_wired=false`, `model_weights_persisted=false`, `utility_proven=false`, `age_authority=0`. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, jepa_weight=0, Age0 RECORD_ONLY. Full Linux suite and independent code review required before any integration; isolated 9 tests do not establish whole-system health.

Exact repeat: `cd v13/code && PYTHONPATH=.:tests python3 -m unittest -v tests.test_world_jepa_heldout_action_readout_20261028 tests.test_world_jepa_action_permutation_control && PYTHONPATH=.:tests python3 -m scripts.world_jepa_heldout_action_readout_20261028 --synthetic-smoke --steps 400`. Use isolated NumPy 2.2.6; do not train on private/live store or modify registered original controls. Next substantive experiment: preregister a **fresh heldout source** and compare fixed-readout action sensitivity versus the direct baseline with paired seeds; do not claim a benefit from one synthetic dataset. If other paths block, continue canonical JEF/C3/B1/B2/Context OS/Dream work.

Actual remaining platform budget: UNKNOWN; this checkpoint is intermediate, not end-of-project acceptance.
