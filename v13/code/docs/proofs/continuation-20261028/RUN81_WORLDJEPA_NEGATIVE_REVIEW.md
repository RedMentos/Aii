# Run81 — independent negative-result review and build-state delta (2026-10-28)

Owner GPT-6 scheduled continuation. Review-only child of Run79 #986 exact head `3c8bb02d79f27c66010bdf02222b4392570ad1c1`; source-only report, **no new training or source change**. Parent chain: Run76 #983 `2fa443822f99b367d137f0254e69e20268f664e8` → Run77 #984 `cdb99f73c6d3af39ddd4e88dd8952cad636fed58` → Run78 #985 `7f7cdc1a9c35a72267955f20e3b6480a717650c2` → Run79 #986. Do not merge into production or alter frozen cohorts without independent review.

## Exact independently audited raw

| Run | Actions | ZIP SHA256 | CRC / manifest | Source tests | Private backup readback |
|---|---|---|---|---|---|
| 76 | 40780438158 | `411a3058acb3b7d0d055d15ef8556f078a1d00c7d77ce45d9bc8d79452ed7692` | CLEAN 17/17 | 19 focused, 2651 full OK (1 skipped), privacy CLEAN | BYTE_EXACT |
| 77 | 40781248191 | `1f87cb3dd42d87001d9200735a9a33d28520c5b586fadecf90df1936c05a65c5` | CLEAN 17/17 | 24 focused, 2656 full OK (1 skipped), privacy CLEAN | BYTE_EXACT |
| 78 | 40781536797 | `6f4a9d55f87a27d8c30e5c565650dea16d290f9518d56320c9291e52be1bb0b0` | CLEAN 22/22 | 28 focused, 2660 full OK (1 skipped), privacy CLEAN | BYTE_EXACT |
| 79 | 40781785429 | `21e5b61fc7fdb67ecd1ce25a1909b71d08de0460d02ffa52fb5ae48685c019e8` | CLEAN 22/22 | 32 focused, 2664 full OK (1 skipped), privacy CLEAN | BYTE_EXACT |

All original stage exit files zero. ZIPs are privately retained under `/V13-Checkpoints/Run7*_CI_RAW_*`; names distinguish negative empirical outcomes from software GREEN. Original raw JSON and per-seed data are unchanged. Independent arithmetic recomputation of all Run78/79 aggregates from each per-seed report passed.

## Result (frozen, do not posthoc retune)

Run78, three preregistered new seeds 401/409/419, actual isolated temporary-file actions, heldout action/slot pairs: member0 target-slot normalized latent MSE **0.68735955391474**; true ensemble mean **0.923358653811138** (**34.334% worse**). Every seed worsened. Mean with shuffled actions **1.6382396042289045**; action signal exists in this narrow latent metric, but ensemble averaging was worse. Exploratory 5% improvement criterion **FALSE**.

Run79, new seeds 431/433/439, train-only supervised readout from the same fitted slotwise JEPA (not JEPA-only): member0 grounded target-slot observed-feature MSE **0.3031085571997498**; mean **0.32455020555249164** (**7.074% worse**); shuffled test actions **0.3292292625790151**; non-JEPA slot-local ridge **0.08485945483170348** (substantially better). Only one of three seeds saw a tiny mean gain. Exploratory criterion **FALSE**. A correct arithmetic ensemble mean is a semantic API correction, **not** a supported predictive or grounded utility improvement. Do not switch runtime defaults.

Potential mechanism to test separately, **not proven**: first predictor gets 240 training steps; bootstrap predictors get 120. Averaging weaker members can degrade predictions. No posthoc new weights, thresholds, cohort/seed changes in registered results.

## Build-state delta (additive, not global rewrite)

- `scope = LINUX_REAL_TEMPORARY_FILE_SHADOW + SYNTHETIC_SOFTWARE`; `source_disjointness_verified = false`; `native_model_executed = false`; `Redmi_measured = false`; `runtime_wired = false`.
- `Age0 = RECORD_ONLY`; `STEP2 = UTILITY_FAIL`; `B3_L1 = FAIL`; `Body_JEPA = UNAVAILABLE`; `LP3 = FAIL`; `jepa_weight = 0`; `canonical_architecture_complete = false`; `user_full_scope_complete = false`.
- `Run76 confidence calibration = OPEN`: `fit` sets `op_err` to zeros before heldout `calibrate`; confidence must not be trusted or given authority before calibrated source binding.
- Claude Z12c independent C5 per-query Spearman remains unverifiable from aggregate-only reports; original Run75 RED and Run80 test-only portability GREEN tracked separately. No authority promoted.

## Next owner / exact commands

Current owner GPT-6 scheduled continuation, review-only. Next independent canonical priority: move from isolated slotwise prediction to **source-bound observed-outcome utility** or another organ's existing roadmap work; avoid unregistered retuning of Run78/79. Before any runtime coupling, obtain source-disjoint real-action outcome benefit against persistence/slot-local ridge and action shuffle; check original negative gates and device prerequisites.

Exact reproduction (from Run79 branch, pinned dependencies):
```bash
cd v13/code
PYTHONPATH=.:tests python -m unittest -v tests.test_run77_slotwise_ensemble_mean tests.test_run78_realfile_ensemble_comparison tests.test_run79_realfile_grounded_readout
PYTHONPATH=.:tests python scripts/run78_realfile_ensemble_comparison.py
PYTHONPATH=.:tests python scripts/run79_realfile_grounded_readout.py
```
These commands execute new real temporary-file actions and require NumPy. They are not phone/native/production acceptance tests. Remaining platform budget **UNKNOWN**.
