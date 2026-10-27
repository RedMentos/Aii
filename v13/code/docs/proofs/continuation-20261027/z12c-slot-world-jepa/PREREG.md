# WP-Z12c PREREG: slot-wise World-JEPA (fix of the Z12b design flaws)

Written 2026-10-27 before any measurement run on the seeds below. Dev seed 7 was used only to debug the code (one run,
numbers not evidence; one BOOT constant changed afterwards: ERR_REF .5 -> 1., because .5 called 80 % of queries uncertain).
Thresholds below are fixed now and are not changed after the run.

## What Z12b got wrong (BEFUND z12b-world-jepa)
1. One latent for the whole folder and the action as one (op, slot) one-hot: an operation known on other slots was not
   composed with a slot it was never taken on (held-out retrieval .27).
2. Attribution compared one pooled latent distance with a threshold per operation. The NO_ACTION control got the same
   per-operation threshold, i.e. it was handed the action identity, so W6 could not separate the two (design flaw).
3. Noop output drifted on states slightly off the training distribution (38 % false alarms when nothing happened).

## Change (v13/world_jepa_slots.py, SHADOW, NumPy)
- Every slot is encoded by the same encoder (10 -> 32 -> 8) and predicted by the same residual predictor
  [z_s, a_s] -> 48 -> 8; a_s = op one-hot for the slot the action touches, class UNTOUCHED for all other slots and for
  every slot under noop. EMA target encoder (tau .99), loss = Z12b's (MSE to target latent + variance/covariance guard +
  inverse dynamics a_s from [z_s, z_s']) on (state x slot) rows. 3000 steps, batch 128 states.
- Confidence: coverage of the operation (count over all slots) x 1/(1 + (bootstrap spread + sqrt(typical error of that
  operation on clean validation transitions)) / ERR_REF) x worst-slot OOD term.
- Attribution, JEPA: SELF iff the touched slot's error <= theta[op] and every untouched slot's error <= theta_untouched
  (99th percentiles of the model's own errors on clean validation). The action decides which threshold applies; that is
  the model using its action. Control NO_ACTION: model trained with every slot UNTOUCHED, ONE threshold on the worst
  slot (99th percentile on clean validation), no action information anywhere.
- Claim limit: the slot split is given (objects are the 6 file slots, not discovered); no interactions between slots
  are modelled.

## Setup
Data collection exactly as Z12b (scripts/z12b_world_jepa.py: real file operations, independent world process with own
seed and wall clock, 4 held-out (op, slot) combinations per seed, counterfactuals executed for real in folder copies,
own noop probability 1/3 in the attribution phase). Fresh seeds 201, 202, 203 (never run before). Per seed 4000
transitions (10 % validation), 150 counterfactual states x 6 candidates, 300 attribution intervals. Controls trained
identically: NO_ACTION (all UNTOUCHED), SHUFFLED_ACTION (action rows permuted). Information only: the Z12b monolithic
model on the same data. Script: scripts/z12c_slot_world_jepa.py.

## Criteria (all must hold for Z12C_SLOT_WORLD_JEPA_PASS)
- C1 covered counterfactual retrieval >= .80 pooled and >= .70 in every seed (Z12b W1, unchanged).
- C2 held-out (op, slot) combination retrieval >= .70 pooled and >= the better control on held-out queries + .30
  (Z12b: .27).
- C3 NO_ACTION and SHUFFLED_ACTION covered retrieval each <= .40 pooled, JEPA minus the better control >= .30 (Z12b W2).
- C4 no collapse in every seed: effective rank of the slot target latents >= 3 (of 8) and min per-dimension std >= .05.
- C5 Spearman(confidence, latent error) <= -.30 pooled over all counterfactual queries (covered and held-out).
- C6 attribution JEPA: own-only SELF >= .90, world-only WORLD_INVOLVED >= .90, nothing-happened SELF >= .80 (Z12b W5).
- C7 the action-free NO_ACTION control's balanced attribution accuracy is at least .20 below the JEPA's.
FAIL stays FAIL. Claim limit: small synthetic-content file world on the cloud machine, given slot split, no phone
measurement, not wired into the runtime (SHADOW module only).
