# Independent exact-parent JEF policy full-suite baseline control (2026-10-31)

Owner GPT-6 scheduled continuation. This review-only branch starts from original **PR #1413 HEAD `2c0ddbf22b6a92f9e0760cbf9af5f8ddd6e51ca9`**, before JEF policy isolation PR #1422. Commit/read back this prereg before workflow. Do **not** modify any production/source/test/Canon blob. Add only this prereg and an isolated workflow.

**Question:** PR #1423 full unfiltered suite on JEF policy child ran 4616 tests, 4 failures, 66 errors, 28 skips (Actions 41175500095, original ZIP SHA256 `aee143795316319f9945a52d8892bbbb5b0d2ca0432cc1e34751e5ab7e6cf3ae`). Are these failures already present in the exact source parent, or did CLI-only policy isolation introduce new regressions?

**Controlled comparison:** same Ubuntu 24.04, Python 3.12, NumPy 2.2.6, psutil, PyYAML, Pillow, prompt-toolkit 3.0.52, torch 2.5.1+cpu, transformers 4.44.2, peft 0.13.2, exact `PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py'` command, no filters or waived tests, same timeout and privacy/diff checks. Same source-handoff/native artifact prerequisites as fresh scratch; do not silently manufacture missing ZIP. This parent lacks the **new** four policy-isolation tests, so total tests need not match 4616 exactly. Compare normalized test identities and failure categories rather than raw totals only.

**Acceptance:** terminal raw ZIP with HEAD/pins, all stage exits, full logs, SHA256SUMS, privacy CLEAN and private byte-verified backup. A parent RED does not make child GREEN; classify exact overlapping failures, new child-only failures and missing prerequisite categories. If child-only regressions exist, fix child in a new preregistered review package. Preserve every original failure and all negative gates. No native C3, Redmi, STEP2, B3, JEPA or production promotion.

Heavy concurrency group `v13-native-c3-ag12-20261030` only after confirming no active owner; this is a software full suite, not a native model pilot.
