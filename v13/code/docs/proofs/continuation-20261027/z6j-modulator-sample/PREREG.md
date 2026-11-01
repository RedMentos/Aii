# WP-Z6j PREREG: typed modulator credited per sample (G-MODULATOR-SPECIFICITY-001, follow-up of Z6f)

Written 2026-10-27 before embedding the real item pool (pool seed 47) and before any run on seeds 211-215. A dry run on
random clustered vectors (not the real encoder, 2 seeds) only checked the code; its numbers are not evidence.

## Why
Z6f (`Z6F_MODULATOR_REAL_FAIL`): the Neuromod gate sets one budget per path from the signals that recently reached it, so
in a path that mixes clean and wrong label sources typing changes almost nothing. The blueprint formula is per sample
(Δθ_i ∝ e_i × δ_i × M_i × P_i). New pure function `v13.neuromod.sample_factor` computes M of one sample with the same
§35.3 kind weights, §63 source credibility and safety veto as the path gate (BOOT priors, not tuned on this bench).

## Setup (identical to Z6f except the weighting)
- 640 generated German questions (z6b templates, 4 routes × 160), real Needle embeddings, real scaffold self-labels.
- Same 600-event stream, same label sources and two mixes, same shift (gist → both from event 300), same softmax learner.
- Arms, each a weight per sample: `v13_sample` (sample_factor), `scalar_sample` (clamp(sum of channels)), `human_sample`
  (human_correction), `outcome_sample` (max outcome channel), all three controls with the safety veto kept as in Z6f;
  `gradient_only` (1), `gradient_only_matched` (mean budget of v13_sample). Reported: `v13` (path gate), `v13_datamix`.

## Criteria (all for `Z6J_SAMPLE_MODULATOR_PASS`), seeds 211-215
- M1 self_heavy: v13_sample >= each of scalar_sample, human_sample, outcome_sample + .03, higher in >= 4/5 seeds.
- M2 self_heavy: v13_sample >= gradient_only_matched + .03, higher in >= 4/5 seeds.
- M3 balanced: v13_sample not more than .02 below any per-sample control or gradient_only_matched.
- M4 v13_sample mean final accuracy >= .70 in both mixes (unchanged from Z6f).
- M5 v13_sample >= v13 (path gate) + .03 in both mixes, higher in >= 4/5 seeds.
- If M1-M3 pass but M4 or M5 fails: `Z6J_SPECIFIC_BUT_WEAK` (typing is specific, the learner/encoder is too weak or the
  path gate is not beaten). Otherwise `Z6J_SAMPLE_MODULATOR_FAIL`. FAIL stays FAIL.
- The gate G-MODULATOR-SPECIFICITY-001 may only be marked as measured-pass with `Z6J_SAMPLE_MODULATOR_PASS`, and only for
  this learner kind; runtime learners do not use per-sample weights yet (no default change from this bench).

Claim limit: label sources and their mix are simulated; one learner kind (route readout); cloud; no phone.
