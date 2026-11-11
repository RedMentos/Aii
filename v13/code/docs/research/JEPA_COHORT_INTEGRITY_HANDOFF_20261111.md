# JEPA cohort-integrity follow-up — 2026-11-11 02:00 Europe/Berlin

Owner: Research & Perception. Review-only child of research-perception/jepa-replay-ablation-20261110-1457 / PR #1687. No production runtime or active gates changed.

## Confirmed defect from source review
The existing `verify_disjoint` compared only caller-supplied IDs and SHA256 of state+action rows. It did not validate finite numeric values, per-field dimensions, repeated observations inside a split, or signed-zero aliases. Thus malformed evaluation cohorts could be admitted; e.g. a NaN in a target was never examined, and +0/-0 state bytes could evade row identity checks.

## Candidate repair
`scripts/jepa_bounded_replay_ablation_20261110.py`: reject empty/malformed dimensions (4 state, 2 action, 4 target), nonnumeric/nonfinite data, duplicate IDs, duplicate state/action observations within train or heldout, and overlap between train and heldout after signed-zero canonicalization. Keep no model/weight changes.

`tests/test_jepa_bounded_replay_ablation_20261110.py`: two new tests with NaN, Inf, short arrays, duplicate observations and signed-zero cross-split counterexamples. Prior four tests retained.

## Evidence and limitations
GitHub source commits are published, but full local test execution was **BLOCKED**: this execution container cannot resolve github.com, so no complete repository checkout. Tests and CI are **UNVERIFIED**, not PASS. A focused read-only CI workflow from parent PR #1687 may run on a new PR, but inspect exact-head status before claiming success.

Next: `cd v13/code && python -m unittest -v tests.test_jepa_bounded_replay_ablation_20261110`; compileall and privacy scan; inspect exact-head Actions. Independently check signed-zero and dtype coercion counterexamples. Reconcile with #1687 and JEPA owner before integration. Existing SourceHandoff freeze, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Age0 RECORD_ONLY and jepa_weight=0 remain. No Android, native training, or JEPA utility evidence.
