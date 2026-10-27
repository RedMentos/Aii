# World-JEPA fixed-budget experiment — 2026-10-27 (review-only)

**Owner:** `codex/automation11-world-budget-ablation-20261027`, child of PR #661 at exact `676b910f68f503a97d289d597080826202e8329f`; draft PR #662. Not main, AG5 or Claude integration. Preregistration `v13/code/docs/proofs/continuation-20261027/world-budget-ablation/PREREG.md` committed **before** implementation/results (`37cbfbd3709029106fb4f55c196b12db7454c962`).

## Exact inputs and software

Original Actions 40453512115 ZIP SHA256 `f3f5eef1d0257c60438d80bf79508494a802f98d94e965f96fac4cf92c909be8`; original seed212 240-row real Linux synthetic-content file-world, first 192 training and 48 clean later calibration rows. Original 10-step checkpoint SHA256 `955ee6efd0eaf2f85803297773ad016d54a33c7c707cd0406b3ceb23739d5e51`; source SHA256 `bff9efa8995b82152c2de853581572991e1bfb8852af792cb02544f584f4b770`. Exact 160-row original heldout cohorts seeds313/314/315, same immutable source/checkpoint/seed/hash and independent timing receipts.

New opt-in `scripts/world_jepa_budget_ablation.py` trains four independent from-scratch models, steps **10, 50, 200, 800**, seed212 and unchanged hyperparameters. Each is calibrated only on original later clean rows, saved in a new SHA/provenance-bound SHADOW-only checkpoint, reopened before heldout evaluation. All original files are read-only and SHA checked; no model/world actions during evaluation, no runtime default/approval/Age change. Seven tests include original byte preservation, restart and tamper counterexamples. CI is pinned to NumPy 2.3.5, one CPU BLAS thread.

## Verified positive exploratory signal — NOT a utility gate

Actions **40456356170** at `b4ff9215203ee2307fef60c9d56a4a9c1faa1126`: 7/7 focused tests PASS; VERIFY/COMPILE/PRIVACY exit0. Raw ZIP artifact ID **12712422347**, SHA256 `8413b6abcdd2651c0e3346f348f0372b13dc4a407199e29a7e24cb9c1f23979a`, CRC clean, HEAD and all four exits checked. Independent **NumPy-only reference with no V13 imports** recomputed all 36 action/identity/rotated MSE values across four arms × three seeds and matched saved scores within **1e-12**. Reference source SHA256 `ecd12a27c0ea1290ae0e549fd0c5b5053a214c8a563cbdd67f9abddbed1d5a62`; JSON SHA256 `03d7796c5c005a0a1e93be7ce5990582b1a9d6690979fb0db1b41318125b357e`. Original and new ZIP hashes independently checked. Private Library copies of new raw ZIP and both reference files at `/V13-Checkpoints/2026-10-27/World-Budget-Ablation/` were re-materialized and byte-exact SHA-verified; no rejected anyone-writable Drive used.

| Steps | Action MSE | Identity MSE | Rotated MSE | Action / Identity | Action / Rotated | Beats both controls (seeds) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 0.31348981 | 0.27064647 | 0.32804098 | 1.15830 | 0.95564 | 0/3 |
| 50 | 0.20408855 | 0.26261371 | 0.25592531 | 0.77714 | 0.79745 | 3/3 |
| 200 | **0.08690503** | 0.26639610 | 0.27815863 | **0.32622** | 0.31243 | **3/3** |
| 800 | 0.10299894 | 0.28984396 | 0.37355607 | 0.35536 | **0.27573** | **3/3** |

**Interpretation:** The frozen 10-step checkpoint was undertrained for this narrowly defined predictive metric. Fixed 50/200/800-step arms all beat both identity and rotated controls in all three *previously collected* heldouts. The 200-step arm has lowest absolute action MSE and action/identity ratio in this one seed/cohort; 800 is worse on that ratio. Different arms learn different latent encoders, so compare within-arm control ratios, not raw cross-arm latent MSE as a universal utility scale. All four arms still report **479/480 SIMULATION_UNCERTAIN**. This is evidence of limited heldout action-conditioned prediction in a Linux synthetic-content file world, **not** semantic/causal generalization, production utility, native Body-JEPA, Redmi performance, or AGI.

**Original failed attempts retained:** Actions 40456176817 failed before training because original verifier's exact-float replay comparison failed; Actions 40456288978 also failed despite strict 1e-10 tolerance on one runner. No original byte/hash changed and no silent threshold widening. The subsequent 40456356170 passed with zero replay deltas for all seeds. The runner-dependent discrepancy remains an open reproducibility question; do not erase these RED receipts or infer universal bitwise replay.

## Integrity and remaining work

Original registered Z12c C1/C2/C3 FAIL remains untouched. STEP2 `UTILITY_FAIL`, B3 `L1_FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Age/approval and full-system negative gates remain. No automatic runtime default change or branch merge.

Next: **preregister genuinely new independent Linux file-world holdouts** for a frozen 200-step candidate (selected after viewing these results, disclose selection); verify the exact 200-step checkpoint hash and all original source/seed receipts, run without training/calibration, compare action vs identity and rotated controls on all new seeds. Independently review and coordinate separate AG5/World two-conflict integration. Full broad software suite is a separate workflow; its final result must be recorded before claiming broad green.

**Exact replay command:** `cd v13/code && V13_FROZEN_WORLD_ROOT=/path/to/closed V13_BUDGET_OUTPUT_ROOT=/new/outside/path PYTHONPATH="$PWD:$PWD/scripts" python3 -m unittest -v tests.test_world_jepa_budget_ablation` (trains four models once). For read-only persisted verification: `python3 scripts/world_jepa_budget_ablation.py --frozen-root /path/to/closed --output-dir /path/to/existing --verify-only`.
