# Run367 — exact current-chain full suite: **RED, preserved**

## Scope and immutable source
- Parent `codex/ag12-finite-confidence-20261025` @ `91416e63c1b9813e9aa3e140e85bd256092adcdc`, measurement review PR #362, not merged to main.
- Exact Actions checkout `9df12a9d9032805aab7921da9b6c104ccfb3e654`, workflow run `40232222383`, job `121286187469`.
- Canon SHA256 check `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee` PASS. Original Run147 native ZIP `12585363362` retrieved **read-only**, SHA256 `ddd60c897e1bdc634a40179b67e434097bb1e1999a6a2141372f6272682b9676`, CRC/member validation PASS. Isolated pinned numpy/prompt-toolkit/CPU torch dependencies installed. `SOURCE_EXIT=0`, `DEPS_EXIT=0`, compileall PASS, `PRIVACY_EXIT=0`/CLEAN.
- Source SHA256 bound in `RUN367_SOURCE_SHA256SUMS.txt`: `agi/base.py` `0a380539...`, `agi/solver.py` `ceeb551d...`, `organ.py` `908ec645...`, and both Run365/366 regression files.

## Actual full-suite result and root-cause classification
- **3,134 tests in 270.635 s: 0 assertion failures, 63 errors, 14 skipped. Overall RED, suite exit=1.**
- All 63 error traces grouped from complete raw output:
  - **36** `ValueError: Live sources differ from complete baseline/candidate` — historical native-firing candidate exact source contract, incompatible with current live source bytes.
  - **26** `ValueError: Runtime is neither exact frozen baseline nor complete reviewed candidate` — historical source-handoff exact baseline/candidate guard, incompatible with current live source bytes.
  - **1** `ModuleNotFoundError: No module named 'test_lp3_serial_cohort'` — historical LP3 helper absent from this checkout's import path (the older Run255 workflow staged a pinned copy in temporary storage).
- No model inference/training or Redmi proof was run by the suite. The 62 historical exact-source errors must not be "fixed" by silently changing pinned baseline hashes or weakening guards. A separate approved integration/replay protocol is needed; the missing LP3 helper can be staged read-only in a future independent workflow. Do not treat 0 assertion failures as suite PASS.
- Prior Run355 at another source head had 3,094 tests, 3 failures, 63 errors, 14 skipped; the two runs are **not a controlled comparison** and do not prove a causal improvement.

## Durable evidence
- Raw Actions artifact `12613203996`, name `V13-Run367-ExactHead-FullSuite-Raw-c092beb7c0b5a277a360388f2d261354ba9bb930`.
- Downloaded ZIP SHA256 `1325380605cee8bf63abb79c559533229f18ebcb1e958286e6da913e002279c6`; CRC and **13/13** internal SHA manifest entries PASS.
- Uploaded to private Library `/V13/checkpoints/2026-10-25/V13_Run367_FullSuite_RED_raw_sha13253806.zip`, re-materialized and byte-compared equal. GitHub artifact retention is temporary; private copy is persistent.
- `canonical_architecture_complete=false`, `user_full_scope_complete=false`, STEP2/B3/Body-JEPA/jepa_weight and Redmi negative gates unchanged.

## Next work
Continue independent canonical functional/native packages while the historical exact-source suite remains RED. Do not overwrite active source owners, retune frozen cohorts, or block unrelated progress on these known historical tests. If attempting LP3 replay, use the pinned Run20 code-only tar and hash-verified Run21 helper from the existing Run255 workflow in a private temporary directory, then rerun **all** tests and preserve original failures.
