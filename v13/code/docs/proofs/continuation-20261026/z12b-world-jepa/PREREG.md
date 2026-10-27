# WP-Z12b PREREG: action-grounded World-JEPA on real file actions (§29 item 13, §7.2)

Written 2026-10-26 before any measurement run on the seeds below. Dev seed 7 (small sizes) is used only to debug the code;
its numbers are not reported as evidence. Thresholds below are fixed now and are not changed after the run.

## Question
Z12a showed self/world attribution on real files with an exact hash prediction (no learned predictor). Can a small
learned latent world model (JEPA: online encoder, action-conditioned predictor, slow EMA target encoder, loss only in
latent space, variance/covariance guard against collapse) learn real action effects well enough to
(a) tell apart the real outcomes of actions it did not take (counterfactuals executed for real in copies),
(b) say when it does not know (coverage / counterfactual confidence), and
(c) replace the exact hash in self/world attribution?

## Setup
- World: a folder with 6 file slots. Own actions are real file operations (atomic write via tmp + os.replace like the WP-K
  sandbox, append, remove, noop): ops write_short, write_long, write_digits, append, remove (x 6 slots) + noop.
  Content text is random per call (the model cannot predict the words; it must ignore unpredictable detail).
- An independent OS process ("world", own seed) writes/appends/removes files on its own wall-clock schedule during data
  collection and during the attribution phase. Its log (time, op, slot, whether it changed anything) is ground truth.
- Observation: 10 features per slot read from disk (exists, is_dir, log length, character class fractions, lines,
  3 hash dims of the content) = 60 numbers.
- Held-out actions: 4 (op, slot) combinations never taken during training (coverage test).
- Model (NumPy, phone-capable): encoder 60->64->16, predictor [z, op one-hot, slot one-hot]->64->16 residual,
  EMA target (tau .99), loss MSE(pred, stopgrad target) + variance hinge + off-diagonal covariance + inverse-dynamics
  head (action from [z, z'], weight 1, §7.2.1); Adam, 3000 steps, batch 256.
  Ensemble: 4 more predictors on bootstrap samples with the encoder frozen; spread -> confidence.
- Confidence = coverage(count of that (op,slot) in training, T8 formula) x 1/(1+spread/SPREAD_REF) x state-OOD term.
  Below CF_MIN = .5 a counterfactual is labelled SIMULATION_UNCERTAIN.
- Controls trained identically: NO_ACTION (action input zeroed) and SHUFFLED_ACTION (actions permuted across transitions).
  Informational only: an observation-space ridge predictor.
- Dev seed 7 (debug only) found two problems, fixed before this prereg was committed: (1) counterfactual states came
  from a different walk than training (many folders, OOD), now the walk uses the training policy; (2) without the
  inverse head the latent kept the untouched slots and dropped the changed one (retrieval ~.5 on dev); with it ~.8 on
  dev. Hyperparameters were not tuned further (dev variants: more steps, Z=32, inverse weight 3 - none adopted).
- Seeds 101, 102, 103. Per seed: 4000 training transitions with the world process running, 150 counterfactual states
  with 6 candidate actions each (every candidate executed for real in a copy of the folder, world not running there),
  300 attribution intervals with the world running (own noop with probability 1/3).
- Counterfactual retrieval: for each candidate action, the prediction is matched to the nearest real outcome latent in
  that candidate set; correct if that outcome's file snapshot equals the true outcome's snapshot.
- Attribution: distance between the prediction for the own action and the observed next latent; SELF if <= theta,
  theta = 95th percentile of the same model's errors on clean own validation transitions of the same operation
  (noop, write_short, ...; dev seed 7 showed one global theta is as large as a whole world change); else WORLD_INVOLVED.
  own-only = own effecting action and no effective world change in the interval; world-only = own noop and an effective
  world change wholly between the two folder reads; intervals where a world change overlaps a read are left out
  as ambiguous (count reported).

## Criteria (all must hold for Z12B_WORLD_JEPA_PASS)
- W1 covered-action counterfactual retrieval >= .80 pooled and >= .70 in every seed.
- W2 NO_ACTION and SHUFFLED_ACTION retrieval each <= .40 pooled, and JEPA minus the better control >= .30.
- W3 no collapse in every seed: effective rank of target latents >= 4 (of 16) and min per-dimension std >= .05.
- W4 Spearman(confidence, latent error) <= -.30 on covered counterfactual queries pooled, and every query for a held-out
  (op, slot) is labelled SIMULATION_UNCERTAIN.
- W5 attribution with the JEPA predictor: own-only SELF >= .90 and world-only WORLD_INVOLVED >= .90 pooled, and
  nothing-happened intervals (own noop, no world change) SELF >= .80 (no false alarms; dev seed 7 had .58).
- W6 NO_ACTION control attribution balanced accuracy at least .20 below the JEPA balanced accuracy.
FAIL stays FAIL. Claim limit: small synthetic-content file world on the cloud machine, no phone measurement, not wired
into the runtime (SHADOW module only).
