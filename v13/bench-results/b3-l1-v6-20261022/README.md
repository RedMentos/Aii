# B3 L1 attempt 6 (WP-Z4d): replication of the escalate PASS on two fresh seeds (cloud, 2026-10-22)

Script `code/scripts/b3_l1_v6_bench.py` (calls the attempt-5 `run_task`/`main` unchanged, only the data seed is swapped), preregistration `code/docs/proofs/b3-l1-v6-20261022/preregistration.json` (commit `b17b8ec` on branch `claude/project-thread-y2mnt5`, pushed before any state was computed). Data seeds 20261201 and 20261202, 600 rows each, 0 sender texts shared with attempts 3/4/5 or with each other; new B1 LFM2.5-1.2B / B2 Qwen3.5-0.8B states per seed (hashes `bb741ebb…` / `57d19977…`, llama.cpp b10964 `9abf88ae…`, all checked).

## Result (private view, accuracy %)

| Task | seed | NO_MSG | EXACT | label word | attr words | SCALAR | **LATENT** | utility vs attr words | canon |
|---|---|---|---|---|---|---|---|---|---|
| escalate (target) | 20261201 | 69.3 | 76.7 | 74.5 | 84.5 | 90.8 | **86.2** | +0.015 ± 0.031, 3/5 | **FAIL** |
| escalate (target) | 20261202 | 60.2 | 81.0 | 77.7 | 81.3 | 89.2 | **85.5** | +0.040 ± 0.023, 4/5 | **FAIL** |
| apologize | 20261201 | 61.3 | 86.5 | 84.5 | 85.5 | 92.7 | 89.3 | +0.036 (sig.), but vs EXACT +0.051 ± 0.036 n.s. | FAIL |
| apologize | 20261202 | 59.2 | 83.5 | 82.3 | 90.7 | 92.3 | 91.2 | +0.003 ± 0.014 | FAIL |
| action | 20261201 | 39.2 | 61.8 | 81.7 | 76.2 | 83.5 | 87.5 | label +0.055, attr +0.111 | **PASS** (also strict) |
| action | 20261202 | 40.7 | 69.0 | 82.3 | 73.8 | 82.0 | 85.3 | label +0.027 ± 0.018 n.s. | FAIL |

All other gate criteria (beats NO_MESSAGE, shuffled/random controls, CONTROL, role retention drop 0, receiver OOD ≤ 5 %, reload identical) hold everywhere; the only failing criterion is the margin over the best symbolic baseline (or over EXACT for apologize seed 1).

**Preregistered verdict: private/escalate NOT_REPLICATED (canon PASS on 0 of 2 fresh seeds).** The attempt-5 PASS is treated as a seed effect. B3_LATENT stays unavailable, L2 stays locked; no L2 prefix SHADOW on escalate.

- apologize: NOT_REPLICATED (0/2; never passed).
- action: SEED_DEPENDENT. Across the four fresh-data attempts it passed on 2 (attempt 4, seed 20261201) and failed on 2 (attempt 5, seed 20261202).
- Shared view (control): only `action` passes, on both seeds, as before.

## What the numbers say (observation, not preregistered)

LATENT is ahead of the attribute words on escalate on all three fresh seeds (+0.056, +0.015, +0.040 utility) and on apologize on all three (+0.003, +0.036, +0.003), but the gap is 1 to 4 points with n = 120 test rows per split seed, so it clears the paired mean − 2 se rule only sometimes. SCALAR (2 × fp16 privileged estimates) stays 3 to 5 points above LATENT on escalate/apologize. The limiting factor is no longer the readout (the attempt-5 fix keeps its +2 to +4 points over the attempt-4 recipe here too) but statistical power and the strength of the symbolic baseline. A further readout tweak on the same 600-row design is not worth another attempt; a next step would need more test data per seed (power) or a task where symbolic words cannot carry the graded quantity.

## Run notes (honest)

- Seed 20261202 was interrupted by a container restart during the private/action task (`run.interrupted.log`). Its cached `states.npz` was reused and the identical script/settings were run again from the start of the training phase (`run.log`); the private/escalate and apologize numbers of the interrupted and the complete run are identical, so the restart did not change results.
- Report bug: the field `overlap.same_sender_text_as_attempt5` in both `report.json` reads 600 because the script compared against attempt 5 after replacing the data seed. Recomputed post hoc: 0 shared texts with attempt 5 for both seeds (as in the preregistration). The data hashes in the reports match the preregistration.
- Runtime 95 + 81 min (states about 19 min per seed), Linux x86_64 cloud CPU, 4 threads. States (about 240 MB per seed) only in the project folder (`v13/bench-results/b3-l1-v6-20261022/seed*/states.npz`).

Claim limits as attempt 5: L1 receiver-adapter read only (no backbone injection), synthetic templates, aux targets are privileged labels, oracle EXACT span, not Redmi.
