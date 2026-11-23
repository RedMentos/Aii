# B3 L1 gate: exact diagnosis of the FAIL + fix candidate (cloud, 2026-10-20)

Question: why does G-CALLOSUM-UTILITY-002 (L1) fail in all three attempts although the learned 64 B message clearly carries information (beats NO_MESSAGE by +9 to +31 points)?

Data: cached B1/B2 states of attempt 3 (`b3-l1-v3-20261012/states.npz`, sha256 `df80c17b…587d2`, project folder only), same 600 rows, 5 paired seeds, fit/select/test 360/120/120, private view. Gate, utility and byte weights unchanged (`v13/b3bridge.py`). Attempt-3 numbers reproduce bit-for-bit (seed 0 LATENT 0.8583 etc.).

Status: **exploratory**. The test items were already seen by attempt 3, so nothing here is a canon L1 verdict. `B3_LATENT` stays `unavailable`, L2 stays locked, no bridge manifest written.

## 1. Preregistered diagnosis (`code/scripts/b3_l1_diagnose.py`, prereg `code/docs/proofs/b3-l1-diagnose-20261020/preregistration.json`, committed before the run) → `report.json`

| Task (depends on) | NO_MSG | SYMBOLIC label | SYMBOLIC attr | SCALAR | ORACLE U,F | LATENT | LATENT refit head |
|---|---|---|---|---|---|---|---|
| escalate (U) | 67.8 | 77.3 | 83.7 | 90.8 | 96.0 | 77.0 | 79.0 |
| apologize (F) | 52.7 | 79.7 | 84.7 | 93.5 | 97.7 | 80.5 | 83.3 |
| action (U,F) | 47.7 | 81.3 | 79.8 | 83.8 | 92.2 | 78.2 | 80.2 |

- **H1 bytes: confirmed, not the cause.** Byte cost of 64 B vs a label word differs by 0.0038 utility; the observed accuracy gaps are 0.02–0.14.
- **H2 head asymmetry: not supported** (rule ≥ 3 points on ≥ 2 tasks). Giving LATENT the same refit head as the baselines adds only +2.0 / +2.8 / +2.0 points; forcing the baselines through the frozen-head residual costs them 0–2.7 (attr) and up to 7.7 (SCALAR). A small part of the gap, not the cause.
- **H3 supervision (probe criterion): not supported in its preregistered form** – and that is the key finding: the bridge message **does** carry the needed quantity. Ridge R² from the 32-dim message vs from sender PCA-16: U 0.88 vs 0.91 (escalate bridge), F 0.94 vs 0.96 (apologize bridge), U/F 0.92/0.90 vs 0.91/0.96 (action bridge). Each bridge carries what its task needs, but drops what it was not trained on (escalate bridge F R² 0.57, apologize bridge U R² 0.37).
- **H4 ceiling:** ORACLE U,F reaches 96 / 98 / 92 %, so there is room above SCALAR.

## 2. Post-hoc addendum (not preregistered; `b3_l1_diagnose_addendum.py`) → `addendum.json`

If the content is in the message, why is the accuracy lower? LATENT_PROBE = the **same 64 B message**, decoded on the receiver side with a ridge U/F probe (privileged labels, exactly the supervision SCALAR gets) → refit head:

| Task | fit items | LATENT | LATENT refit | **LATENT probe** | SCALAR | SYMBOLIC attr |
|---|---|---|---|---|---|---|
| escalate | 180 / 360 | 79.3 / 77.7 | 81.5 / 79.0 | **85.2 / 89.0** | 88.2 / 90.8 | 79.3 / 83.7 |
| apologize | 180 / 360 | 79.8 / 81.3 | 80.7 / 83.3 | **89.3 / 92.7** | 91.2 / 93.5 | 77.8 / 84.7 |
| action | 180 / 360 | 75.2 / 78.8 | 74.0 / 80.2 | **78.3 / 86.2** | 79.0 / 83.8 | 72.5 / 79.8 |

LATENT_PROBE vs SCALAR: −1.8 / −0.8 / +2.3 points, none significant. **The 64 B message content is as good as the best symbolic channel; what loses is the learning signal.** The bridge is trained only from ≤ 360 binary/ternary task labels, while SYMBOLIC_ATTR and SCALAR are trained on privileged graded U/F labels. Doubling the task labels (180 → 360) does not shrink the LATENT-vs-SCALAR gap (escalate 8.9 → 13.1, apologize 11.3 → 12.2, action 3.8 → 5.0 points), so more task labels alone do not fix it.

(LATENT for apologize at 360 items is 81.3 here vs 80.5 in run 1: small BLAS-thread nondeterminism of the bridge training, same code and seeds.)

## 3. Fix candidate: same supervision as the baselines (`Bridge(aux=A).fit(..., aux=…)`) → `aux_explore.json`

`v13/b3bridge.py` gained an optional, training-only auxiliary target: a linear head `Wa` on the receiver projection is trained to predict standardized sender-side attributes (here U and F), so those directions are pulled into the message. Default `aux=0` is byte-identical to before; `Wa` never reaches `receive()` (test `test_aux_gradients_and_receive_unchanged`, finite-difference gradients, reload). Message stays 64 B, receiver path unchanged.

Exploratory run (`b3_l1_aux_explore.py`), same seeds and splits:

| Task | LATENT | **LATENT_AUX** | paired gain | gate vs label word | gate vs attr words | strict vs SCALAR |
|---|---|---|---|---|---|---|
| escalate | 77.0 | **82.5** | +5.5 (5/5) | PASS | FAIL (−0.014) | FAIL |
| apologize | 80.5 | **85.2** | +4.7 (5/5) | FAIL (EXACT) | FAIL (+0.003, n.s.) | FAIL |
| action | 78.2 | **88.0** | +9.8 (5/5) | PASS | PASS | PASS |

Shuffled/random controls stay at chance (37–56 %), OOD 0.2–1.2 %. On `action`, the exploratory gate passes all criteria including the strict SCALAR comparison; escalate and apologize still fail against attribute words (and apologize against the 429 B EXACT span).

## Result

Exact diagnosis: **The L1 FAIL is not a channel or byte problem. The 64 B message carries the sender quantity (R² 0.88–0.94) and, decoded properly, is as good as SCALAR. The bridge loses because it learns only from a few hundred task labels, while the symbolic baselines get privileged attribute labels.** The frozen-head residual costs another ~2 points. With equal supervision (aux targets) the bridge gains +5 to +10 points and passes the gate exploratorily on `action`.

Consequence: no canon change. Next step is **attempt 4**: preregistered, fresh data seed (new model states needed, B1 LFM2.5-1.2B + B2 Qwen3.5-0.8B as before), bridge with `aux` targets, gate unchanged, role retention re-measured. Only a PASS there allows the L2 SHADOW test.

Claim limits: exploratory on seen test items; role retention not re-measured for LATENT_AUX (receiver path unchanged; set to 0 in the exploratory gate); synthetic templates; Linux CPU cloud, not Redmi; the aux targets are privileged labels, the same kind the SYMBOLIC_ATTR/SCALAR baselines use.

Runtimes: diagnosis 27 min, addendum 33 min, aux run ~30 min (4 CPU threads).
