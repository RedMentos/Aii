# Run90 prereg — BodyTrainPort artifact/descriptor symlink escape guard

2026-10-24. Exact base Run89 PR122 `8a3f5e9487c4c6251ec1e5c5cec1c04fffe92426`, selected Linux 380/380, extracted ZIP 79/79 PASS. Owner: `v13/code/v13/body_training.py` path-bound descriptor inspection only; new `tests/test_body_train_port_paths_run90.py`; focused/extracted CI test invocations; Run90 evidence. Do not touch native runner, model revisions, training rights, Canon, original cohort or other owners.

## Problem and preregistered RED
`inspect_train_port(home, role)` currently checks lexical `..` but then follows `Path.is_file()` and `file_hash()` on symlinks. A manifest can bind files **outside** the declared home via a symlink artifact, symlink parent directory or symlink descriptor, and still report `port_bound=True`. The function always returns `update_authority=0`, so this is a **descriptor provenance/integrity** defect, not evidence of unauthorized training.

First commit real tempfile filesystem tests that expect fail-closed on: (A) artifact symlink to outside with matching hash, (B) symlink parent directory to outside, (C) descriptor symlink outside, (D) `../` descriptor path outside. Existing ordinary in-home bound port must remain `PORT_BOUND_PROOF_REQUIRED`, authority 0. Run tests in actual Linux CI and preserve RED before any fix. Then reject symlink components and out-of-home resolution, without changing TrainRunnerProof or fp32 requantizer exception semantics. Independently review race limits; path checks alone do not prove hostile concurrent filesystem race safety. No models/native/Redmi, no Body-JEPA gate promotion.

Original gates remain STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, complete V13 INCOMPLETE.