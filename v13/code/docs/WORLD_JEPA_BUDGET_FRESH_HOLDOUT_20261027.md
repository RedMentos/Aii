# World-JEPA 200-step candidate: new Linux holdouts — verified 2026-10-27

**Owner:** `codex/automation11-world-budget-fresh-holdout-20261027`, draft PR #663, review-only child of PR #662 at exact base `e310f0fd0ed17175daa9c58207265fda0fe44512`. Preregistration committed **before** any new collection (`04f8b862983166b201dd8a162ecb6ba170124d6a`). No main/AG5/Claude merge.

## Frozen lineage, new data and implementation

Original Linux file-world Actions 40453512115 ZIP SHA256 `f3f5eef1d0257c60438d80bf79508494a802f98d94e965f96fac4cf92c909be8`. Frozen 10/50/200/800 budget Actions 40456356170 ZIP SHA256 `8413b6abcdd2651c0e3346f348f0372b13dc4a407199e29a7e24cb9c1f23979a`. The 200-step candidate was **selected after inspecting** original heldout seeds313/314/315. Selected checkpoint SHA256 `7cb6158b3f39de2d9fa589906c5ed24ce92869709ce18fc09a70f3804e8b20c0`, training seed212, original source SHA256 `bff9efa8995b82152c2de853581572991e1bfb8852af792cb02544f584f4b770`. Original registered Z12c cohorts/seed/hashes untouched.

New `scripts/world_jepa_budget_fresh_holdout.py` verifies both frozen input trees and all four budget checkpoints **before** collecting new data. It runs the unchanged independent Linux temporary file-world process for **predeclared seeds 401, 402, 403**, 160 rows each, preserving original raw rows, independent schedule/log, SHA-bound action timing receipts and manifest. Only read-only SHADOW prediction after collection; no fitting, calibration, model actions, tool/fact writes, age/approval or runtime authority. New `tests/test_world_jepa_budget_fresh_holdout.py` includes eight tests for restart, no original changes, seed integrity, tamper and alias denial.

## Result: independent fresh predictive signal, not semantic utility

Actions **40456753777** at `0ecd9a995365b0e27816f1e1ea1c823768377e41`: **8/8 PASS**, separate persisted VERIFY/COMPILE/PRIVACY exits0, original ZIPs SHA/CRC/path guards PASS. Raw artifact ID **12713510151**, SHA256 `0cd1e9426e7810f17f72bde399268791579e61784e64cb89d3adb4f5b77f1f33`, CRC/HEAD/all four exits verified.

| Fresh seed | Action MSE | Identity MSE | Rotated MSE | Uncertain rows | World-overlap rows |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 401 | **0.09172738** | 0.26955088 | 0.27498687 | 160/160 | 1 |
| 402 | **0.09599784** | 0.25644637 | 0.27453919 | 160/160 | 1 |
| 403 | **0.11655923** | 0.27583076 | 0.28420046 | 159/160 | 6 |
| Weighted 480 rows | **0.10142815** | 0.26727601 | 0.27790884 | **479/480** | 8 |

Action/identity ratio **0.37948842** and action/rotated ratio **0.36496914**. Action prediction beats both controls on **all 3 new seeds**, meeting the **exploratory predeclared** predictive signal. This is an out-of-sample check relative to the previous frozen seed313/314/315 set, but **the 200-step model was selected using that earlier set**. It is not a blinded multi-model comparison, causal/semantic intervention test, calibrated confidence success, native Body-JEPA, Redmi measurement or whole-system utility gate.

Independent local NumPy-only reference (no V13 import, no training) verified exact budget ZIP and 200-step checkpoint hashes, all four fresh raw file SHA per seed, and recomputed all **9 action/identity/rotated MSE values** and weighted results within **1e-12**. Reference source SHA256 `b6098bc379f3934a6e4a246360cb11d740928f32d4ca84dd7cb21ee2bbd069b9`; result JSON SHA256 `3e31443f8d3367168be7a3da147c75412a58f44bd20e9910a05cf88d767a67b3`. New original raw ZIP and both independent reference files were uploaded privately to `/V13-Checkpoints/2026-10-27/World-Budget-Fresh-Holdout/`, re-materialized and verified byte-exact. No rejected anyone-writable Drive destination was used.

## Open gates and next package

**All negative gates stay unchanged:** STEP2 `UTILITY_FAIL`, B3 `L1_FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Age-0/approval, native/Redmi and canonical/full-scope completion false. The selected 200-step model still labels 479/480 new rows `SIMULATION_UNCERTAIN`; confidence/coverage calibration is not solved. No automatic runtime model swap.

Next highest-priority scientific package: **task-level intervention utility**, not more latent-MSE-only optimization. Pre-register an external-world consequence metric (e.g. predicting which real file slot changed after an action, with no-action and action-shuffled controls), compare the frozen 200-step model against simple deterministic baselines on new independent seeds and evaluate action-specific causal relevance. This is separate from the AG5/World two-conflict integration and Redmi sustained/native tests. Independently review source, failed attempts, original timing receipts, and all negative gates before any promotion.

Exact repeat: `cd v13/code && V13_FROZEN_WORLD_ROOT=/original/closed V13_FROZEN_BUDGET_ROOT=/budget/trained V13_FRESH_OUTPUT_ROOT=/new/outside/path PYTHONPATH="$PWD:$PWD/scripts" python3 -m unittest -v tests.test_world_jepa_budget_fresh_holdout`; persisted read-only check: `python3 scripts/world_jepa_budget_fresh_holdout.py --original-root /original/closed --budget-root /budget/trained --output-dir /fresh --verify-only`.
