# Current review-chain full software-suite triage — prereg 2026-10-27

Base PR #656 exact `3c527cebe70947d910121f8c605b66ba0de810a5`, review-only child. This package first measures, does not silently repair or reclassify failures. Prior inherited notes report a historical broad suite around 4335 tests with 5 FAIL and 73 ERROR on an earlier chain; those counts are NOT assumed current or evidence of source regressions.

Run `python -m unittest discover -s tests -p 'test_*.py' -v` on exact current source with isolated Python 3.12, pinned NumPy 2.3.5 / prompt-toolkit 3.0.52, NO_MODEL_DOWNLOADS/HF_HUB_OFFLINE, bounded 20-minute Actions job, no native model downloads or competing training. Preserve full raw stdout/stderr, exit, HEAD/source SHA, compile and privacy scan in immutable ZIP. Classify each observed failure by missing optional prereq vs actual code/contract, and choose a narrow non-destructive fix only when verified. No registered cohort/model/age/approval changes, no fake native/Redmi proof.

The broad test suite is diagnostic and may fail. A failed run is retained, not called GREEN or used to promote any gate. Any later fix needs a prospective focused RED/GREEN and an independent review. Do not overwrite other owner branches. Next exact command after triage: reproduce the first actionable non-environment failure with its smallest focused test on a child branch.
