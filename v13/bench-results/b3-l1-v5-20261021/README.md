# B3 L1 attempt 5: escalate/apologize with a receiver-conditioned readout on fresh data (cloud, 2026-10-21)

Confirmatory test of the fix found in `bench-results/b3-l1-escapo-diagnose-20261021/`. Script `code/scripts/b3_l1_v5_bench.py`, preregistration `code/docs/proofs/b3-l1-v5-20261021/preregistration.json` (commit `9d52f49`, pushed before any state was computed).

Why escalate/apologize failed in attempt 4: their label needs a receiver-private fact (team capacity / client status) combined with the sender quantity. The bridge read as an additive residual on the frozen NO_MESSAGE readout, whose capacity/client weights were fit without U/F and are attenuated; with the true U/F that costs 8–9 points (diagnosis). Every baseline already gets a jointly refit readout.

What changed vs attempt 4: new data seed 20261105 (600 rows, 0 sender texts shared with attempts 3 or 4), **new B1/B2 states** (LFM2.5-1.2B Q4 `bb741ebb…`, Qwen3.5-0.8B Q4 `57d19977…`, llama.cpp b10964 `9abf88ae…`, all hash-checked), and LATENT = the aux bridge built with `recv_cond` (gated re-weighting of the receiver state while the message gate is open) followed by `Bridge.refit_readout` (open-gate readout refit over [receiver state, gated message projection] on the fit split, L2 on the select split). Message (64 B BF16, K=4 r=8 h=16), gate `b3bridge.l1_gate`, baselines, splits, 5 paired seeds and canon rule unchanged. Gate closed still gives the frozen NO_MESSAGE readout bit-identically.

## Result (private view = target, accuracy %)

| Task | NO_MSG | EXACT | SYMBOLIC label | SYMBOLIC attr | SCALAR | LATENT_AUX (att. 4 recipe) | LATENT_RC_E2E | **LATENT (refit)** | canon | strict |
|---|---|---|---|---|---|---|---|---|---|---|
| escalate (target) | 64.0 | 76.7 | 78.7 | 84.7 | 89.2 | 83.3 | 86.3 | **90.5** | **PASS** | FAIL (n.s.) |
| apologize (target) | 58.0 | 84.8 | 80.5 | 88.5 | 92.3 | 86.0 | 86.3 | **89.0** | FAIL (attr words +0.003, n.s.) | FAIL |
| action (replication) | 40.0 | 67.8 | 83.5 | 79.7 | 84.5 | 86.5 | 87.2 | 86.7 | FAIL (label word +0.028, 4/5, n.s.) | FAIL |

- **Preregistered verdict: L1 PASS on `private/escalate`.** First canon L1 PASS on a task that needs a receiver-private fact. All criteria hold: beats NO_MESSAGE (+26.5), shuffled/random controls (59.3/66.3), utility beats EXACT (+0.161), CONTROL, label word (+0.115) and attribute words (+0.056, 5/5); role retention drop 0.0, receiver OOD 1.0 %, reload bit-identical. Readout refit vs attempt-4 recipe +7.2 points (5/5), vs the same bridge before the refit +4.2 (5/5).
- **`private/apologize` FAIL.** The refit helps (+3.0 vs attempt-4 recipe, 4/5, n.s.; +2.7 vs before refit, significant) and beats EXACT and the label word, but ties the attribute words (89.0 vs 88.5, utility +0.003). On this seed the attribute words are 2 points stronger than in attempt 4 (88.5 vs 86.5), and SCALAR stays clearly better (92.3).
- **`private/action` did not replicate the attempt-4 PASS on fresh data.** Neither the new readout (86.7) nor the attempt-4 recipe (86.5) clear the label word (83.5) significantly on this seed (attempt 4: 90.0 vs 81.5). The diagnosis predicted no gain from the refit on action (receiver adds only noise there), and that holds (−0.0 to −0.5 points). The attempt-4 PASS stays the preregistered result of that attempt, but it is now known to be **seed-dependent**; it should not be treated as robust.
- Shared view (control, receiver also sees the sender text): only `action` passes (canon and strict), as in attempt 4.
- strict SCALAR (2 × fp16 privileged estimates): FAIL everywhere in the private view; on escalate LATENT is +1.3 points over SCALAR (2/5 seeds), on apologize −3.3.

## Consequence

- Per preregistration: **an L2 prefix SHADOW experiment is allowed for `private/escalate`**. That is the task the Z4b result asked for: its label word cannot be computed by the sender alone. LATENT authority stays 0, runtime unchanged (`recv_cond` default off), no bridge installed in any home. `B3_LATENT` stays `unavailable` for apologize.
- New caveat: L1 passes are fragile at n=600 / 5 seeds (action passed on one seed, not on the next). A next L2 step should re-check the escalate L1 PASS on its own seeds first.
- Bridge artifact of the passing task: `bridge_private_escalate_B1_TO_B2.{json,npz}` (sha256 `f23734d3…`, recv_cond 48, readout L2 0.1, 64 B message).

## Evidence and limits

`report.json` (all per-seed numbers, gates, hashes), `run.log`. States (231 MB) only in the project folder (`v13/bench-results/b3-l1-v5-20261021/states.npz`). Runtime 99 min (states 19 min), Linux x86_64 cloud CPU, 4 threads.

Claim limits: L1 receiver-adapter read only (no backbone injection); synthetic templates (same as attempts 3/4, used to design both fixes); aux targets are privileged labels (as for SYMBOLIC_ATTR/SCALAR); the readout refit gives LATENT the same jointly fit readout the baselines already get; oracle EXACT span; not Redmi.
