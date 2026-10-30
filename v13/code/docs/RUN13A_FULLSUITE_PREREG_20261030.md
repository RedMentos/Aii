# Run13A unfiltered full-suite cross-review preregistration — 2026-10-30

Independent review-only child of native PR #1280 at source HEAD `57cb8215ac95484e86a7e9bf1d1d2977aa6a4a35`. Owner GPT-6 automation. This preregistration precedes any Run13A full-suite execution and is not a model/native run.

Purpose: check integration regressions from the new isolated Run13A runner/verifier against the entire current review chain. Run unfiltered `python -m unittest discover -s tests -p 'test_*.py'` from `v13/code` under `PYTHONPATH=.:tests:scripts`, with `V13_NO_AUTOSTART=1`, `NO_MODEL_DOWNLOADS=1`, pinned isolated CPU torch 2.5.1, transformers 4.44.2, peft 0.13.2, numpy 2.2.6, psutil, PyYAML, Pillow, prompt-toolkit 3.0.52. No native model bootstrap, paid provisioning, live tool authority or age promotion.

Preserve **all** test failures and original raw logs, including historical Run34/Run37 source-identity negative tests; do not change frozen source pins, skip those tests, or relabel the full suite GREEN if they fail. Record test counts, failures/errors/skips, import dependency failures, compiler result, Git hash pins, privacy scan and diff check. Source-only Actions run must close SHA256SUMS and upload original ZIP on both PASS and FAIL. Privately back up byte-exact and independently replay manifest before reporting.

Prerequisite before running: finish and audit native Actions `41065858620` or confirm it has stopped; do not overlap this full-suite CPU/ML test with active heavy native/model work. Current negative gates remain Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi UNMEASURED, whole V13 incomplete. Full-suite software success cannot prove semantic complementarity or complete architecture.
