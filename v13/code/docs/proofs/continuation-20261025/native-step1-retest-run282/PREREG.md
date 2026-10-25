# Run282 prereg — serialized actual-weight STEP1 retest (2026-10-25)

## Binding and ownership
- Based on verified PR281 `4995c157c3c578cc12b54b5e6aec80275b8e3d25` after Run280/281 no-B proof isolation patches. Own only new Run282 workflow and this proof directory. No runtime/probe/model/seed edits.
- Public registered model manifest Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99` is byte-identical to PR269 native cohort. `bootstrap.py` `dc23e192bcd01589475692666ebb6568c80d078b`; `acceptance.py` `432b2e33eb53142b0d4246813b96fc791b0900f0`. Actual checkout source hashes differ because new bug fixes; record them.
- Serial heavy job: same concurrency group `v13-native-c3-run131-serialized` as PR269. No overlapping native model job. Linux Ubuntu 24.04 runner, fresh prereqs, pinned isolated CPU dependencies, public model/runner downloads with registered hashes.
- Fixed acceptance command: `python scripts/acceptance.py --installed-home "$V13_HOME" --archive-dir "$RUNNER_TEMP/run282-archive" --stage-limit 4`. Exactly first four registered stages: `jef-modes`, `experience`, `learning`, `executive`. No new cohort or changed thresholds.
- `--stage-limit 4` must finish as `DIAGNOSTIC_INCOMPLETE`, exit code 2, **even if 4/4 stages pass**. Workflow success means bounded native diagnostic completed with these four PASS, not whole-system acceptance. All stage JSON checks must be true; otherwise preserve failure and report FAIL.
- Always preserve raw preflight, bootstrap logs, model/runner provenance, exact checkout SHA, per-stage JSON/logs, acceptance status/exit codes, privacy scan, and source hashes. No fake native execution.

## Prior negative control
- PR269 full native 20 stages, 12 PASS / 8 FAIL, exit 2, `IMPLEMENTED_PATHS_PARTIAL`, raw artifact `12597232047`, SHA256 `eac321b4f8119f0ce10cbd65c050c87e56f11b94ec8d56322f450014f13054d0`.
- JEF combined `runner.role=B1_DETAIL` despite absent body manifest, `combined_c3=false`; executive first C3 false. New Run280/281 software fixes mask committed AG0 B slots in disposable test home. This native run tests their actual effect; no assumption of success.

## Non-promotions and next step
- Original STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, V13 `INCOMPLETE`, Redmi NOT MEASURED. This limited Linux-native run cannot change them.
- After Run282: inspect exact stage JSON and raw, independently review failures. If all four PASS, continue next canonical utility package or serial STEP12 native proof on current chain; do not silently promote full V13. If any FAIL, fix only a reproducible defect with RED-first tests and rerun serially.
