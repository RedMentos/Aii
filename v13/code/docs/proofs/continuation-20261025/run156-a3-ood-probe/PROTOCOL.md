# Run156 A3 OOD stress diagnostic — exploratory, non-promoting

Base Run152 `945a4b3c0d957b8cf5599889e619dd31015d3b99`. Owner: Run156 only new `run156` script, tests, proof and CI. Run152 candidate, frozen `student_worker.py`, Runtime, model artifacts, original source hashes and negative gates remain unchanged.

This **exploratory synthetic test was run locally before this protocol was published**; do not misrepresent it as a pre-registered independent native cohort. It uses NumPy seed 15625, 512 dimensions, 64 training / 64 same-distribution / 64 OOD vectors in each of two regimes: one concentrated cluster with Gaussian noise scale 0.015 and one isotropic uniform-on-sphere regime. Only training vectors determine Run152's threshold. Held-out acceptance is diagnostic, never used for tuning.

Expected failure mode: the inherited [0.5, 0.99] clamp can reject all genuinely same-distribution points when their cosine nearest-neighbor scores are <0.5. Clustered data may work; uniform data may fail. This is a counterexample to universal calibration, not a claim about measured A3 text/teacher utility.

Source research: NumPy `quantile` default method `linear` (https://numpy.org/doc/stable/reference/generated/numpy.quantile); Sun et al., ICML 2022, *Out-of-Distribution Detection with Deep Nearest Neighbors* (https://proceedings.mlr.press/v162/sun22d.html). That paper concerns suitable learned representations and does not validate this A3 hashed stem or threshold.

Next independent evidence: actual A3 `raw_features` source-group holdout with held-out teacher targets, fixed cohort hashes and threshold chosen solely on training sources; then separately consider an integration only after frozen SourceHandoff restrictions clear. All V13 gates remain negative.
