# Run366 GREEN — AG12 confidence is finite and bounded

## Changes and exact source
- Stacked on Run365/PR360 review branch, not merged into main; Run366 PR #361.
- `v13/code/v13/agi/base.py`: shared `clamp01` now maps nonfinite numeric measurements to 0 rather than false certainty; finite behavior unchanged.
- `v13/code/v13/agi/solver.py`: native field confidence checks finiteness, distinguishes invalid numeric metric from missing metric, and bounds every weighted JEF-like coalition vote. Missing confidence still returns the original 0.5 uncalibrated baseline.
- Source/test head `217b5c0eac6a05aa9a148489bc3246e5e2f3fe59`, source SHA256: `agi/base.py` `0a380539a15bda1c4024ab128916f09f6325ddf4ecbc5d5b794aa57bc6b8451e`; `agi/solver.py` `ceeb551dbcde89495241d66fa3fe751225b8d4352fb09fbb3eaf3fe57e1c82a5`.

## Verified RED/GREEN
- Preregistered PLAN `91ab250a1ed1bf91660f2ebe08672964a074daac` before test `23693559b9757b7c68420e47ee1d0b3309cdb23c` and before production changes.
- RED Actions `40231902253`, job `121285224138`, checkout `9da2654caec76273cd71e7bb8b5f7fdc3d152632`: 24 tests, **9 expected assertion/subtest failures**, no fixture errors, inherited AG12/live tests PASS, privacy CLEAN. Raw ZIP artifact `12613616345` SHA256 `22db02444405beaf8234c6a5a6b5767c4a310ac2cdb8915817ad8efc212cc83f`.
- GREEN Actions `40232010426`, job `121285543713`, exact checkout `217b5c0...`: **24/24 PASS in 1.549 s**, compileall PASS, privacy CLEAN. Independent focused source-bound workflow `40232010258` SUCCESS. Raw ZIP artifact `12613461636` SHA256 `0646103072c06765a495e02b589629f5a85b854f6a79adf43ffb66b3d203593f`.
- Both raw ZIPs downloaded independently; CRC and 4/4 internal SHA manifest checks PASS. Both uploaded to the **private Library** and re-materialized with byte-for-byte comparison PASS:
  - `/V13/checkpoints/2026-10-25/V13_Run366_AG12_RED_raw_sha22db0244.zip`
  - `/V13/checkpoints/2026-10-25/V13_Run366_AG12_GREEN_raw_sha06461030.zip`

## Claim limits and next work
- This closes a real software/calibration integrity bug, not a measured improvement in model intelligence. No native model, phone, trained head, STEP2 EXIT, B3, Body-JEPA, jepa_weight or Age promotion.
- `canonical_architecture_complete=false`; `user_full_scope_complete=false`.
- Next independently authorized work: AG12 direct calibration consumers should not accept unbounded/nonfinite external confidence pairs, with strict failure behavior and actual persisted metacognition regressions; alternatively a higher-priority newly integrated functional package if newer owners advance the chain. Do not repeat Run366 tests without a new source change.
