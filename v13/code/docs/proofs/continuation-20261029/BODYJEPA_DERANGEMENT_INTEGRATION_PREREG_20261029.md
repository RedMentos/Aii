# Body-JEPA derangement changed-source regression integration — prereg (2026-10-29)

This is a second, **independent** scoped verification after the 4/4 stdlib-only GREEN, not a retroactive expansion of the original four-test proof.

- Source branch PR #1153, Body-JEPA candidate blob `fe912d908868d5e923297fa52b44e09f1e39bf1f`, Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.
- Existing full PEFT dependency run `40960222503` is in progress at preregistration; **do not launch this tiny-torch job until it completes**, to avoid overlapping model work. Its outcome is unknown.
- Fresh Ubuntu 24.04 isolated venv, pinned official CPU `torch==2.5.1+cpu`, `transformers==4.44.2`, `peft==0.13.2`, `numpy==2.2.6`, existing basic deps; `pip check` and exact import version checks required. No model downloads or private data.
- Run exact focused suite `PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_bodyjepa_derangement_bound_20261029 tests.test_body_jepa tests.test_body_jepa_checkpoint_fit tests.test_body_jepa_checkpoint`. Preserve **all** original raw logs, package versions, source blobs, checksums, privacy/diff, failures and stage exits. No test exclusions, no changed cohorts/seeds.
- Acceptance is scoped software-only pass of those exact tests; any failure remains RED and must be diagnosed. A pass is not real Body-JEPA learning, not Redmi/native, not STEP2/B3/LP3 or whole-system completion. Historical registered cohort and Canon hashes remain untouched.
