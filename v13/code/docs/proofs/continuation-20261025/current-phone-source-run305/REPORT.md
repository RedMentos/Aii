# Run305 — current-chain source-only Termux ZIP: verified and privately backed up

UTC 2026-10-25. Draft PR303, base Run304 verified checkpoint `c0c84fa3a1939e983ec15f3e4bc3ad8ee880afba`. Exact packaged/CI source `ec997fffd1581eec1863729a12620d643f7a5937`. Preregistration was committed first at `4e6ecebcef8846467c550ad0180953ccb7f20655`; workflow at `ec997fffd1581eec1863729a12620d643f7a5937`. No production source changes in Run305.

## Actual Linux software evidence
- GitHub Actions exact-head `40205397748`, job `121205117018`: **PASS**; official public-repo privacy scan **CLEAN**.
- Canon SHA256 pinned `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`; no model/seed/cohort change.
- Canonical `scripts/package_source.py --phone-install` emitted immutable `V13-Phone-Run305.zip`: 12,941,118 bytes, SHA256 `af10d0b67b48487371c16d0826d2a1d4b16df14ee5f2df2a396ea3573f678d23`. 1018 members including manifest; independent verifier counted 1017 source files, uncompressed total 29,280,040 bytes, manifest SHA256 `2c3f87d467f38a6ec7218c2b5a2c2d58f723911e13d6742ba0ec6b912d43a367`.
- Independent ZIP verifier: CRC **PASS**, every member SHA256 **PASS**, checkout byte parity **PASS**, no private/model files, no native inference, no Redmi measurement.
- Extracted `V13-Phone` source: actual `V13_SOURCE_ONLY_DIAGNOSTIC=1` setup **PASS**, Age-0 CLI initialized, explicit `NO_NATIVE_MODEL / NO_REDMi / NO_JEPA_PROOF`, full selftest/model probe **NOT RUN**. Extracted source ran **15/15 PASS** across Run304 backup source closure, Run302 learning status and phone operator/CLI tests.
- GitHub raw artifact `12603961109`, outer ZIP SHA256 `d17832699cb31984e8b74dda05571aea2a72ad41ce3c2b1d5aa0941dcd2b26a8`. Raw logs, exit codes and SHA256 manifest included; all four required exit codes 0. Downloaded back, checked outer SHA, extracted inner ZIP, verified inner SHA, raw SHA256SUMS and ZIP CRC.
- Separate private persistent Library backup: `/V13-Inquisition/Proofs/Run305/V13-Phone-Run305.zip` and `/V13-Inquisition/Proofs/Run305/V13-Run305-Current-Phone-Source-Artifacts.zip`. Both were read back as exact bytes and independently SHA256-checked; no rejected anyone-writable Drive destination used.

## Scope, limitations, next
This ZIP is **source-only**: normal Termux setup still needs its pinned public native/model dependencies and actual Redmi execution to prove the full path. It is not an already running model and does not prove native inference, battery/RSS/thermal or learning utility. STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, V13 `INCOMPLETE` unchanged. Branch-scoped PR303 is not production-integrated main.

Next independent Canon package: test WorldModel's source-level holdout leakage when distinct user events repeat **identical source text**, then (only if RED reproduces) group holdout by source identity without modifying registered unique-source cohorts, model/seed/Canon or source authority. Preserve original Run301 event-group proof and run full related regression. Do not overlap Run303 Budget/Run297 native owners.
