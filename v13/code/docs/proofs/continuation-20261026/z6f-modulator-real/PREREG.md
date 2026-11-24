# WP-Z6f PREREG: typed modulators with a real encoder (G-MODULATOR-SPECIFICITY-001)

Written 2026-10-26 before embedding the real item pool (pool seed 41) and before any run on seeds 201-205. A dry run on
random clustered vectors (not the real encoder) only checked the code; its numbers are not evidence. That dry run
already showed a structural point that this measurement is meant to confirm or refute on real data: the Neuromod gate
scales the plasticity of a whole path from the signals that recently reached it; it is not a per-sample weight, so in
one path that mixes clean and wrong label sources it cannot pick out the wrong samples. The V13 component that filters
per sample is the data-mix guard (arm v13_datamix, reported, not judged).

## Setup
- 640 generated German questions (4 routes x 160, z6b templates), real native Needle embeddings
  (v13.learning_worker.features), self labels from the real scaffold router (v13.cognition.scaffold_route).
- 600 events per seed, one path 'route', a softmax readout with a normalized step (LR0 .5 x arm factor / (1+|x|^2)).
- Label sources: human correction (true), real outcome (true, task_success), self (scaffold), dream (fixed wrong route
  per class, source dream), unsafe success (wrong route, task_success, safety veto). From event 300 the true route of
  gist questions is 'both' (human and outcome follow; scaffold and dream do not). Test: held-out quarter with the new labels.
- Mixes: balanced (human .20, outcome .25, self .25, dream .20, unsafe .10) and self_heavy (.10, .15, .35, .30, .10).
- Arms as v13/ablation99.py: v13 (real gate), scalar_reward, human_only, outcome_only, gradient_only,
  gradient_only_matched (V13 mean budget), v13_datamix (reported only). Safety veto kept in all modulator arms.

## Criteria (all for Z6F_MODULATOR_REAL_PASS), seeds 201-205
- M1 self_heavy: v13 mean final accuracy >= each of scalar_reward, human_only, outcome_only + .03, and higher in >= 4/5 seeds.
- M2 self_heavy: v13 >= gradient_only_matched + .03, higher in >= 4/5 seeds.
- M3 balanced: v13 not more than .02 below any control or gradient_only_matched.
- M4 v13 mean final accuracy >= .70 in both mixes.
FAIL stays FAIL. Claim limit: label sources and mix simulated; one learner kind; cloud; no phone.
