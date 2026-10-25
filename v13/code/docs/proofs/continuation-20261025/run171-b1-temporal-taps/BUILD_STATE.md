# Run171 BUILD_STATE — 2026-10-25 (candidate, pre-native)

Base Run170 `79df0f7e9c1cf0f3a17f08aac4b31ecf01f51911`; owner only new Run171 script/test/workflow/proof. No edits to frozen Runtime/Canon, existing worker, models, cohorts or any active learning state.

Implemented an opt-in read-only B1 native final-token tap capture of **16 precommitted English source groups**, source-group-disjoint t→t+2 pairs, and unchanged external `v13.predictor_worker.train` consumer with frozen B1 weights. Existing worker computes heldout MSE vs copy/shuffle, EMA, finite-difference gradient, noncollapse, deterministic repeat and checkpoint reload. Run171 native CI uses pinned model/runner SHA and shared serialized native concurrency group; private vectors and candidate weights are deleted, metadata only is uploaded.

Local Python 3.13 + NumPy: **5/5 synthetic FakeTap tests PASS**; compileall PASS. Source Git blob `9b647053923534b5dde266a0dc52abb364d613da`; test blob `809322207551d361681b68b442f1f5b1d489565f`. Local raw test SHA-256 `e6a7cf229bdaa43de2c08f375c7477ddf32ec5f27810a5d6c61146278bca9315`. This is not a native result. Prereg source texts SHA-256 `76c0276ed2501a017a10c10c0cbfbc30e97268bee95e910df3388ceccfaa1302`. CI result **PENDING** until checked.

Claim limits: external 16D projector/predictor on frozen B1 2048D native taps, not B1 body-weight learning, not actual answer coupling, not proof of improved responses, not Redmi. No production integration or learning authority. `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`.

Next exact step: verify PR CI, preserve any failures and compare holdout metrics to copy/shuffled baselines; then independently design a native Body train-master path with actual predictive targets and answer-level utility/retention. In parallel, Run164/167 full-suite FAIL (3 LP3 CLI rc1 vs expected2 and one descendant) remains unresolved and must not be marked green.

No user decision required; rejected anyone-writable Drive destination not retried.

## Run171 first CI failure preserved (not a native attempt)

Actions run `40166327260`, job `121088019991` **FAIL** during Python test collection: `ModuleNotFoundError: No module named 'run171_b1_future_states'`. Root cause: local scratch placed script and test together, but the real repository separates `v13/code/scripts` from `v13/code/tests`. The original test inserted its own tests directory in `sys.path`; it could not import the new script in GitHub CI. No model download/native tap/training occurred in that failed run; artifact upload correctly reported no report. The initial test source and workflow blobs remain in Git history.

Fixed only the new test import path, changed to `parents[1] / 'scripts'`. Reproduced in a locally reconstructed real directory layout: **5/5 PASS**, raw log SHA-256 `9c25fd7c1a55f8fdf84db0cd7ce269474416c202c4b2e4a308599da0e1a00157`; new test Git blob `2a769fd578bf70d4410e02f30a4097743b9822b9`. Workflow pin updated accordingly. Native CI must rerun; no claim of native success until actual completion.

## Verified native Linux result — predictive gate FAIL

Run171 Actions `40166406273`, job `121088284944`: **SUCCESS as an executed CI job**, after the first failed import-only run `40166327260` (retained above). Native B1 frozen model/runner hashes checked; 5/5 synthetic tests PASS; native 16-text tap + external predictor executed serially; official privacy scan CLEAN. Metadata-only artifact ID `12587853560`, ZIP SHA-256 `4807c1647a74fb8a29eb48153c6d65ee29a8315c078a6b8d9a869dceb58d8ff6`.

Observed **86 real token-state t→t+2 pairs** from 16 source texts, 2048D. Worker: `gradient_check=True`, `noncollapse_pass=True`, `retention_pass=True`, `deterministic_repeat=True`, `checkpoint_reload=True`, **`predictive_ablation_pass=False`, `commit_eligible=False`**. Heldout MSE before 1.3404576797, after prediction **1.0532468129**, copy baseline **1.0323739542**, shuffled-target **1.0069155399**. The learned predictor is **worse than both controls**; do not label this a gain. EMA target std ratio 0.88435, effective rank 16. No actual answer utility or Body weight learning.

Thus the real native run is complete but **the learning acceptance gate failed**. Keep `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `DS2_H2=FAIL`, `V13=INCOMPLETE`. Exact next: diagnose why the fixed external 16D predictor fails copy/shuffle on the source-group-heldout B1 token states; preregister any new representation/horizon/controls *before* further native runs. A Body train-master objective and answer-level utility remain unimplemented.
