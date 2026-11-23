# JEF human-agreement report: live self-source integrity — verified 2026-10-30

Review-only child of #1234 exact parent `c67edbf29ab45e24037ab2c50b22e88abce23f0f`; includes existing JEF human-receipt fixes from #1226. This is a **real Store/SQLite synthetic software** regression, not a native/model or learning experiment. Owner GPT-6; changed `v13/code/v13/jefoutcome.py` report read model only, one test file, isolated CI and scoped docs. `learning.py`, self training rows, conservative human veto, native paths, age gates and all registered cohorts untouched.

## Confirmed failure and original RED

The existing `training_rows` already refuses revoked, wrong-kind and corrupt self-outcome sources, but `jefoutcome.report` previously counted retained labels as human agreement without checking whether the self source was still live. This could inflate human-overlap/trust metrics after self-source revocation or substitution.

Prereg commit `5a7bb4bd8d0165644c826362bd3270310a8e3584` preceded tests. Initial test-first **Actions 41024134422 RED** at `f02d9437cf23e4c2676051a8a6c69cd3328dc05f`: 34 tests, four errors from missing preregistered `live_labels` metric; artifact **12961929479**, ZIP SHA256 `f854c64c06bbb1b2fc8d0e84de65aab76f936b562081cc71d5963931665d6917`, CRC clean and 13/13 inner hashes. Test-order addendum explicitly committed *after* this RED; it changed assertion order only, not expected behavior. Posthoc diagnostic **Actions 41024277789 RED** at `4d542c746899e521b007fa54f6d072e7fd4549a2`: **two actual false human-overlap reports** for revoked and wrong-kind self source, plus two missing-metric errors; artifact **12962039328**, ZIP SHA256 `080797253ed3eeadee4642f8dcbb2fafb17e7e435b0732b397e8e4aaefb79110`, CRC clean and 13/13 hashes. Both original RED ZIPs privately saved and byte-reverified. This second run is posthoc diagnostic, not retroactively preregistered.

## Fix and GREEN

Read-only helper `_live_self_label_source` now verifies each retained outcome source is active, kind `OUTCOME_SELF_LABEL`, and its exact source bytes match the stored label through `Store.read_source`. Report keeps `labels`/`by_value` as **historical** counts and adds `live_labels`; only live labels contribute to `human_overlap`/`human_agreement`. It does not change training admission, human authority or source revocation behavior.

**Actions 41024398241 GREEN**, exact tested HEAD `1044ada8c54dcefd38b9c145ef4ba6237965e31e`, artifact **12963077272**, ZIP SHA256 `88b99c93dd2a99ade87e715d535d4b5de0ed24b09105cd82f1fecd9966be63b0`. **34/34 PASS**, all six VENV/DEPS/TEST/COMPILE/PRIVACY/DIFF stages exit0, privacy CLEAN, CRC clean and 13/13 inner hashes. Existing JEF human-receipt, human RECORD precedence/window, self source, report source, and outcome tests included. Real Store, no native model; no optimizer training. Private Library backup `/V13-Checkpoints/2026-10-30/Run11-JEF-ReportSelfSource/` contains both original REDs and GREEN; all three re-materialized SHA256 byte-identical.

## Gates, limitations, next

Age0 `RECORD_ONLY`, STEP2 `UTILITY_FAIL`, B3 `NO_PROMOTION`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Redmi `UNMEASURED`, whole V13 `INCOMPLETE`. No full unfiltered suite, native or phone run claimed; historical `labels` remain counts, not verified live evidence. Draft review branch; do not auto-merge.

Next: independent cross-review of report semantics and source bytes, then Context OS/JEF/Body-JEPA end-to-end canonical packages. Exact focused rerun: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_jef_report_self_source_run11 tests.test_jef_human_receipt_integrity_20261030 tests.test_jef_human_report_receipt_integrity_20261030 tests.test_jef_human_record_precedence_20261030 tests.test_jef_human_record_window_20261030 tests.test_jefoutcome_self_source_20261030 tests.test_jefoutcome_report_source_20261030 tests.test_jefoutcome`. The branch CI workflow also records raw and SHA256SUMS.

**Checkpoint is intermediate, not whole-system completion.** Remaining platform budget UNKNOWN.
