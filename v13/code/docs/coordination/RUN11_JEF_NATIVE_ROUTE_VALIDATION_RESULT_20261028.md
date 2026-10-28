# Run11 JEF C2 native route validation candidate — 2026-10-28

**Owner / scope:** GPT-6 isolated review-only runtime candidate based on #850 `b454f81da33de9d621af6417ed47ab55cba6263f`, prereg `722709d8830bc728cff099a4b7780c6af4ae1983` before edits. Not integrated into production main, #848/#849 Age0 native prompt branches or source-frozen #857 transfer64.

## Functional source change

The old `Runtime._route` recursively traversed all native C2 response fields and treated any `route` enum as a valid proposal, even unrelated metadata or a different tool. The candidate adds `_validated_native_route(control)`, reusing existing `control_calibration_worker.observation` to accept only the first successful, finite-confidence, validated `select_processing` route. Invalid observations return no native proposal, keep the scaffold, and mark `native_control_rejected=True`. Existing human override, external approved head, Executive admissibility, calibrated-confidence support and scaffold-simple-only override remain untouched. **No new native C2 authority** or confidence calibration is granted.

New synthetic tests cover valid first route, unrelated wrong-name tools and metadata, negation/ungrounded/failure/nonfinite confidence, scaffold fallback, valid advisory, and no override of detail scaffold. The tests use fake runtime components and **do not load native models**.

Source blob: `v13/code/v13/runtime.py` candidate `bcc8d8ccd3f6d4032949237ce89d1a969759c7e1`; original source blob `68e7ed1352800174972558f1e0b0683a42c8689a` remains on original review branches. New test blob `1e1ffdd2f7740bc1f1f569e066d524e9f24d7f9c`. Existing observation blob `1b353cf79ca2291c6ec4cf7b69eb926a63a1b48b` unchanged.

## Evidence and continuation

Source-pinned GitHub Actions workflow `run11-jef-native-route-validation-20261028.yml` staged. **CI pending/unverified** until run and raw artifact checked; no native JEF rerun and no Redmi. The source-level counterexample is real for the old recursive parser, but no evidence proves it occurred in previously recorded native runs. Next: inspect CI focused/full tests and raw hashes; independent code review; if GREEN, separately preregister a new-source Linux JEF native proof and eventual Redmi measurement before integration.

All negative gates remain `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `LP3_heldout=FAIL`, `jepa_weight=0`, `Age0=RECORD_ONLY`, `phone_measured=false`, `whole_system_complete=false`.
## First Linux CI result — RED preserved

Run **40643051790** at `8448c7387dfd6a172989cbc819d69045208ffc0d` completed **FAILURE**. Source pins, install, **20 focused tests**, compile, privacy scan CLEAN and diff all exit0. The **full suite is RED**: `Ran 2221 tests in 203.209s; FAILED (failures=4, errors=62, skipped=1)`. Failure traces include source-handoff/native-firing/phone-package fixtures that intentionally require the exact frozen `runtime.py` blob and reject any unregistered candidate runtime (`Runtime is neither exact frozen baseline nor complete reviewed candidate`; `Live sources differ from complete baseline/candidate`). This is a real compatibility/acceptance blocker, **not** silently marked an unrelated test failure or GREEN. The synthetic JEF validation tests passed, but full integration remains unproved.

Closed RED ZIP artifact `12797235103`, SHA256 `053ac6fa4859980332293f3835332de45037181e41451631a6bcd25f41941a1b`, CRC clean, **16/16** internal SHA256SUMS valid, private Library backup `/V13-Checkpoints/2026-10-28/Run11-C2-Paired-Audit/JEF_NATIVE_ROUTE_SOFTWARE_RED_40643051790_sha053ac6fa.zip` re-materialized byte-exact. All failed raw preserved. Do not modify old source-handoff hash pins or count an exclusion-only run as full-suite PASS. Next: investigate a separately reviewed source-bound integration plan that preserves old frozen cohorts; meanwhile continue independent canonical work. No native/Redmi/production promotion.
