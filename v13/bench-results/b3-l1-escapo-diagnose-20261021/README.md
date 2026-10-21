# B3 L1: why escalate/apologize fail while action passes (cloud, 2026-10-21)

Exploratory diagnosis on the attempt-4 states (`b3-l1-v4-20261021/states.npz`, project folder only; data seed 20261021, private view, 5 paired seeds, fit/select/test 360/120/120). The test items were already used by attempt 4, so **nothing here is a canon verdict**. Script `code/scripts/b3_l1_escapo_diagnose.py`, committed (2f18789) before its run, hypotheses and rules in its docstring.

## Structural difference

escalate = U > thr[capacity], apologize = F > thr[client]: the label needs a **receiver-private fact** combined with the sender quantity. action is sender-computable (receiver adds nothing; NO_MESSAGE 41.5 %).

The bridge reads as an additive residual on the **frozen NO_MESSAGE readout**. That readout was fit without U/F, so its capacity/client weights are attenuated (U/F act as noise). A sharp message term a·U needs a matching receiver term a·thr[capacity]; the frozen term cannot be rescaled, so the per-capacity threshold blurs. Every baseline (EXACT, SYMBOLIC, SYMBOLIC_ATTR, SCALAR) gets a jointly refit readout over [receiver state, feature].

## Result (accuracy %, mean of 5 seeds)

| Task | NO_MSG | ORACLE U/F refit | ORACLE U/F frozen | SCALAR refit / frozen | ATTR words refit / frozen | LATENT (attempt-4 recipe) | LATENT + recv_cond (end to end) | **LATENT, same message, refit readout** |
|---|---|---|---|---|---|---|---|---|
| escalate | 65.3 | 97.8 | 89.7 | 89.3 / 87.2 | 84.5 / 83.3 | 83.0 | 85.3 | **91.0** (+8.0, 5/5) |
| apologize | 60.0 | 98.5 | 89.2 | 93.7 / 88.5 | 86.5 / 85.2 | 85.0 | 86.7 | **90.5** (+5.5, 5/5) |
| action | 41.5 | 89.7 | 95.2 | 85.2 / 87.2 | 76.7 / 76.8 | 90.0 | 90.8 | 89.0 (−1.0, 0/5) |

- **D1 frozen-head cost: confirmed.** With the true U/F, the frozen residual loses 8.2 (escalate) and 9.3 (apologize) points against a refit readout; on action it is *better* (−5.5: the receiver state only adds noise there). This is exactly the structural split between the failing and the passing tasks.
- **D2 receiver fact:** capacity and client are decodable from the receiver state at 100 % – the information is there, only the readout combines it wrongly.
- **D3 fix candidate:** end-to-end training of a gated receiver re-weighting (`Bridge(recv_cond)`) helps only a little (+2.3 / +1.7). Refitting the open-gate readout jointly over [receiver state, gated message projection] – the same readout the baselines get – helps a lot (+8.0 / +5.5, all seeds) and lands above the attribute words (84.5 / 86.5) and near SCALAR.
- **D4 error locus:** 72 % / 78 % of LATENT errors are within 1 of the threshold (near-threshold items are 33 % / 39 % of all items): the message is roughly right, the boundary is placed badly.

## Consequence

Fix = `Bridge(recv_cond=dim)` + `Bridge.refit_readout(...)` (both default off, frozen runtime unchanged; gate closed still gives the frozen NO_MESSAGE readout bit-identically, tests in `tests/test_b3bridge.py`). Confirmatory attempt 5 preregistered on fresh data seed 20261105 (`code/docs/proofs/b3-l1-v5-20261021/preregistration.json`, pushed before any state was computed): see `bench-results/b3-l1-v5-20261021/`.

Claim limits: exploratory on seen items; synthetic templates; Linux CPU cloud, not Redmi. Runtime 38 min.
