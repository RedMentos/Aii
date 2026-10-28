# Run11 JEF C2 native route validation candidate — 2026-10-28

**Owner / scope:** GPT-6 isolated review-only runtime candidate based on #850 `b454f81da33de9d621af6417ed47ab55cba6263f`, prereg `722709d8830bc728cff099a4b7780c6af4ae1983` before edits. Not integrated into production main, #848/#849 Age0 native prompt branches or source-frozen #857 transfer64.

## Functional source change

The old `Runtime._route` recursively traversed all native C2 response fields and treated any `route` enum as a valid proposal, even unrelated metadata or a different tool. The candidate adds `_validated_native_route(control)`, reusing existing `control_calibration_worker.observation` to accept only the first successful, finite-confidence, validated `select_processing` route. Invalid observations return no native proposal, keep the scaffold, and mark `native_control_rejected=True`. Existing human override, external approved head, Executive admissibility, calibrated-confidence support and scaffold-simple-only override remain untouched. **No new native C2 authority** or confidence calibration is granted.

New synthetic tests cover valid first route, unrelated wrong-name tools and metadata, negation/ungrounded/failure/nonfinite confidence, scaffold fallback, valid advisory, and no override of detail scaffold. The tests use fake runtime components and **do not load native models**.

Source blob: `v13/code/v13/runtime.py` candidate `bcc8d8ccd3f6d4032949237ce89d1a969759c7e1`; original source blob `68e7ed1352800174972558f1e0b0683a42c8689a` remains on original review branches. New test blob `1e1ffdd2f7740bc1f1f569e066d524e9f24d7f9c`. Existing observation blob `1b353cf79ca2291c6ec4cf7b69eb926a63a1b48b` unchanged.

## Evidence and continuation

Source-pinned GitHub Actions workflow `run11-jef-native-route-validation-20261028.yml` staged. **CI pending/unverified** until run and raw artifact checked; no native JEF rerun and no Redmi. The source-level counterexample is real for the old recursive parser, but no evidence proves it occurred in previously recorded native runs. Next: inspect CI focused/full tests and raw hashes; independent code review; if GREEN, separately preregister a new-source Linux JEF native proof and eventual Redmi measurement before integration.

All negative gates remain `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `LP3_heldout=FAIL`, `jepa_weight=0`, `Age0=RECORD_ONLY`, `phone_measured=false`, `whole_system_complete=false`.