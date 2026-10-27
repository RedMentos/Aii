# World-JEPA independent heldout utility: verified review checkpoint — 2026-10-27

**Owner:** codex/automation11-world-holdout-utility-20261027, review-only child of PR #659 `949afa149460478661d54cfa944e321d195a7b03`. No owner/main or AG5/Claude merge.

## Concrete implementation

New `scripts/world_jepa_holdout_utility.py`: opt-in `run` collects a NEW real Linux temporary file-world cohort after loading the exact previously calibrated v2 checkpoint; no model fit, calibration, learning, live tool or Age authority. It verifies training export timing receipts and source/model/provenance before file-world actions; requires a different seed. It compares target-latent normalized action-conditioned MSE against target-encoder identity/no-change and one-row-rotated action controls. Confidence/OOD inference is capped to 16-row batches (original unbounded OOD broadcast reproduced as RED). It saves raw cohort, independent process schedule/log, SHA-bound action intervals, manifest and exact checkpoint/source binding. `verify` reopens original files in a separate process and recomputes timing/metrics; `summarize` refuses duplicate/tampered cohorts and reports weighted descriptive multi-seed comparisons. All outputs are SHADOW_ONLY, authority=0, no automatic promotion.

Usage from `v13/code` after creating an independently verified training export:

```sh
PYTHONPATH="$PWD:$PWD/scripts" python3 scripts/world_jepa_holdout_utility.py run --training-export /path/to/training-export --output-dir /path/to/fresh-heldout --seed 313 --rows 160
PYTHONPATH="$PWD:$PWD/scripts" python3 scripts/world_jepa_holdout_utility.py verify --training-export /path/to/training-export --output-dir /path/to/fresh-heldout
PYTHONPATH="$PWD:$PWD/scripts" python3 scripts/world_jepa_holdout_utility.py summarize --training-export /path/to/training-export --exports /path/to/heldout313 /path/to/heldout314 /path/to/heldout315
```

The `run` command deliberately creates real files in a NEW isolated Linux temporary directory. It is not a Redmi command or a live operator action. The `verify` and `summarize` commands are read-only. Do not reuse seed212 for heldout against training seed212.

## Closed evidence and results

- First real heldout CI GREEN: Actions `40453259711` at `b77c2dd`, 6/6 tests, independent verifier/compile/privacy CLEAN. Original raw ZIP SHA256 `7899b9ae2ca0fc2168044686b7b1f44643bd3802080bfa6e0aa88c967a575c66`.
- Memory counterexample RED: Actions `40453332879` at `9f6eb3a`, 7 tests 1 FAIL exactly `unbounded OOD batch` at `model.confidence`; other verifier/compile/privacy exits 0. Original ZIP SHA256 `1a43e0713028d03677fd57399d9456d5d433b4764175646c3fc1521c615ec081`. GREEN `40453356805` at `e0397c3`, 7/7 tests.
- Fixed-seed follow-up: Actions `40453512115` at `d99ceab6714e9bd5abf6587a3c9603173743b929`, 9/9 tests PASS, separate-process VERIFY for 313 and 315 exit0, RUN315 exit0, multi-seed SUMMARY exit0, compile0, privacy CLEAN. Original ZIP SHA256 `f3f5eef1d0257c60438d80bf79508494a802f98d94e965f96fac4cf92c909be8`, ZIP CRC clean, 42 files, all 24 closed source/cohort/log/checkpoint hashes independently checked.
- Private Library bytes saved and re-materialized byte-exact: `/V13-Checkpoints/2026-10-27/World-Holdout-Utility/` (first GREEN, RED and final multi-seed ZIPs). The rejected anyone-writable Drive destination was not used.
- Final training: real file-world seed212, 240 rows, 48 calibration rows, checkpoint SHA256 `955ee6efd0eaf2f85803297773ad016d54a33c7c707cd0406b3ceb23739d5e51`, cohort SHA256 `484ba3e1175800eeb1a21bbbb8e308721368b3391dc2e27811bd288e29d363dd`, source SHA256 `bff9efa8995b82152c2de853581572991e1bfb8852af792cb02544f584f4b770`. Evaluator source SHA256 `fd467f399be8bac51256c33e07c02bce1ed4823d802eae30267fbe54bec05df5`, test SHA256 `b139055ae9aedc6eddd4d0faecc658151783a4b6bae52528f2be96d65be46179`.
- Final fresh heldouts: seeds 313, 314, 315, each 160 transitions (480 total). **Action prediction MSE 0.31348981 versus identity 0.27064647 (worse in 3/3), versus rotated action 0.32804098 (better in 3/3)**. Weighted deltas action minus identity **+0.04284334**, action minus rotated **-0.01455117**. 479/480 SIMULATION_UNCERTAIN. This is **negative** for beating a simple identity baseline, despite some action sensitivity.
- The first seed313 observation was inspected before selecting 314/315; follow-up is exploratory, not a blinded preregistered significance claim. Real Linux timing changes the seed212 training cohort and checkpoint between separate CI runs; the 3 final heldouts share the **single** exact checkpoint above, but are NOT a byte-identical replay of the earlier seed313 training run. No native Body/Redmi/semantic utility proof.

## Preserved failures and negative gates

The original initial workflow failed before tests due malformed GitHub expression interpolation (Actions `40453029681`); corrected without deleting logs. Intermediate canceled runs remain visible. The OOD RED is retained, not overwritten. No changes to registered Z12c seed211 C1/C2/C3 FAIL or original model/source/seed hashes. STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Age-0 approvals and canonical/full-scope completion remain unchanged and negative.

## Open questions and exact next work

1. A fixed-checkpoint, same-heldout **ensemble-mean vs first-predictor** ablation (separate opt-in evaluator, no default model change) may reveal whether the first-member choice is responsible for part of the identity deficit. Predeclare controls before observing.
2. Stratify errors by operation/slot and actual independent world overlap; check whether a narrow operation group beats identity while overall result fails. No gate promotion from posthoc slices.
3. Independently review this PR and integrate with the separate AG5/World two-conflict candidate without overwriting other owners. Original registered Z12c gates, native Body/Callosum learning and Redmi sustained evidence remain separate.

**Next command (once review branch available):** `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python3 -m unittest -v tests.test_world_jepa_holdout_utility`; then inspect the preserved `MULTISEED_RAW.json` and checkpoint `955ee6ef...` in the private artifact before choosing a new frozen ablation. Do not re-label these exploratory scores as a PASS.
