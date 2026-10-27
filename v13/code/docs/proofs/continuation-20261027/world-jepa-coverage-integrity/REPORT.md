# WP-Z12b World-JEPA train-bound confidence — review checkpoint

2026-10-27 UTC. Draft PR #748, child of PR #746 exact `13355020dc13b45bc4096446b65568bd50f4e385`. Prereg `5796addd7755432774b724837ce2a8e12449f550` was committed and fetched before test/source changes. Scope: only `world_jepa.py`, five new software tests, dedicated CI workflows and this proof folder. No runtime, weight, seed, master or gate changes.

## Independent counterexample and fix

The pre-fix `WorldJEPA.confidence` used the supplied sample count directly. An action absent from all training rows could be labeled `MODEL_SIMULATION` at confidence **1.0** by supplying 1000; malformed count/action/state/spread/OOD and broadcast batch shapes were not rejected. Original test-only RED Actions `40549725719` at `30dd10ccb6c1bb25a54e6703022b1686019d1e74`: **9 tests, 4 inherited PASS, 5 expected FAIL**. All original failures retained, no claim of GREEN. Raw Actions artifact `12753963101`, ZIP SHA256 `552014d3ce33076e58c4a274e7bfd7df661c3686e49688fead5ffda40e34106f` (GitHub Actions 30-day retention; no private backup claim).

Minimal fix at `e3de852f572d531a1a748dcf88c2c990558f63aa`, source blob `5ffd56097e66a37e2922e39d1dc0ba86cb28a760`: `fit` records exact one-hot training action counts; confidence uses caller counts only as a conservative upper bound, zeroes malformed evidence, rejects mismatched shapes, clamps finite confidence to [0,1]. Original predictor/encoder/EMA/optimizer untouched. GREEN focused Actions `40550021728`: **9/9 PASS**, all INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits 0, raw artifact `12755021449`, ZIP SHA256 `5a68d5774c7bc5e474e7b65b06a0da7c9bbac752a4b18cf36b7afbcd5a58bbb3`. Source fetched back from GitHub, blob SHA matches.

Full software suite Actions `40550351354` was launched at exact source/workflow commit `50c0a73c22d53eeb708a491f7c6b26cddd492d8d`; **PENDING** at this checkpoint, no full PASS claim yet. Review its raw exits/artifact before integration.

## Gates and continuation

Software/synthetic only. World-JEPA remains SHADOW and not runtime-wired. LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; `jepa_weight=0`; Age authority 0; Redmi unmeasured; V13 incomplete. No main merge. Independent review required.

Next command (read-only): inspect `https://api.github.com/repos/RedMentos/Aii/actions/runs/40550351354/jobs`, then the run artifact and five raw exit files. If full suite succeeds, append closure without rewriting the original pending observation. Continue the separately preregistered heldout action/ensemble experiment on child branch `assistant/v13-world-jepa-heldout-20261027` (not part of this guard's claim).
