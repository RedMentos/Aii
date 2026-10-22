# B3 L1 attempt 4: aux-trained bridge on fresh data (cloud, 2026-10-21)

Confirmatory test of the fix candidate from `bench-results/b3-l1-diagnose-20261020/`. Script `code/scripts/b3_l1_v4_bench.py`, preregistration `code/docs/proofs/b3-l1-v4-20261021/preregistration.json` (commit `eaf49b7`, pushed before any state was computed).

What changed vs attempt 3: new data seed 20261021 (600 rows, 0 sender texts shared with attempt 3, same templates and rules), **new B1/B2 states** (LFM2.5-1.2B Q4 sender `bb741ebb…`, Qwen3.5-0.8B Q4 receiver `57d19977…`, llama.cpp b10964 release binary `9abf88ae…`), and LATENT = bridge trained with the training-only aux target (standardized sender-side U, F). Gate `b3bridge.l1_gate` unchanged, 64 B message, K=4 r=8 h=16, 5 paired seeds, fit/select/test 360/120/120. The attempt-3 recipe without aux runs alongside as `LATENT_NOAUX` (reference only).

Runner check before the run: 6 attempt-3 rows recomputed, receiver states bit-identical to the attempt-3 cache, sender token states rel. L2 difference 0.9 % (CPU kernel/batch numerics).

## Result (private view = target)

| Task | NO_MSG | EXACT | SYMBOLIC label | SYMBOLIC attr | SCALAR | LATENT_NOAUX | **LATENT (aux)** | canon | strict vs SCALAR |
|---|---|---|---|---|---|---|---|---|---|
| escalate | 65.3 | 80.3 | 77.7 | 84.5 | 89.3 | 78.0 | **83.0** | FAIL (attr words −0.017 utility) | FAIL |
| apologize | 60.0 | 84.7 | 82.0 | 86.5 | 93.7 | 81.0 | **85.0** | FAIL (vs EXACT/label not significant) | FAIL |
| action | 41.5 | 70.7 | 81.5 | 76.7 | 85.2 | 80.0 | **90.0** | **PASS** | FAIL (utility +0.045, not significant) |

- **Preregistered verdict: L1 PASS on `private/action`** – first canon L1 PASS of G-CALLOSUM-UTILITY-002 in four attempts. All gate criteria hold: beats NO_MESSAGE (+48.5), shuffled/random controls (at chance), utility beats EXACT (+0.216), CONTROL, label word (+0.082) and attribute words (+0.131); role retention drop 0.0, receiver OOD 1.3 %, reload bit-identical.
- escalate and apologize **FAIL**, as predicted by the exploration: the aux bridge gains +5.0 / +4.0 points (5/5 and 4/5 seeds) but stays below the three-level attribute words on utility.
- aux vs no aux, paired: +5.0 / +4.0 / **+10.0** points, significant on all three tasks. The diagnosis (training signal, not channel) is confirmed on fresh data.
- strict SCALAR (2 × fp16 privileged U/F estimates, claim-limit add-on): FAIL everywhere in the private view; on `action` LATENT is +4.8 points more accurate than SCALAR (3/5 seeds) but the utility gain is not significant. Shared view (control): `action` passes canon and strict.

## Consequence

- Per preregistration: **an L2 prefix SHADOW experiment is allowed for `private/action` only**. LATENT authority stays 0, the runtime is unchanged, no bridge is installed in any home. `B3_LATENT` stays `unavailable` for the other tasks; nothing beyond L1 is claimed.
- Bridge artifact of the passing task: `bridge_private_action_B1_TO_B2.{json,npz}` (sha256 `3c75aad1…`, 29 233 params, 64 B message). Manifest note: `b3bridge.save` kept the reload check's dummy revisions `s`/`r`; corrected in the JSON after the run and fixed in `v13/b3bridge.py` (fresh fields now win, test added). Weights and sha256 are unaffected. The script run used `b3bridge.py` as preregistered (sha in `report.json`).

## Evidence and limits

`report.json` (all per-seed numbers, gates, hashes), `run.log`. States (231 MB) only in the project folder (`v13/bench-results/b3-l1-v4-20261021/states.npz`). A first start of this run was killed by a container restart before any state was saved (log kept in the project folder, not counted).

Claim limits: L1 receiver-adapter read only (no backbone injection); synthetic templates, the same ones used to design the aux fix; aux targets are privileged labels (the same kind SYMBOLIC_ATTR/SCALAR get); oracle EXACT span; Linux x86_64 cloud CPU (4 threads), not Redmi. Runtime 94 min (states 20 min).
