# Run35 prereg — C3 native report arm-to-envelope binding review (2026-10-28)

**Base:** Run34 review PR #943 at exact parent `47a079d50170ea03c8abf6d96ac240dbc6caedea`; isolated child review branch `assistant/v13-run35-c3-report-arm-binding-review-20261028`. Do not change Run33 cohort, seeds, model/runner pins, frozen Runtime, Store, B1/B2 or canonical acceptance gates. Run34 native has NOT been run on this branch.

**Defect hypothesis:** `run34_c3_native_quote_intervention_pilot.verify_report` independently validates a row's declared arm and its envelope but does not require `row.arm == row.envelope.arm`. A synthetically rehashed report can attribute one preregistered C3 prompt to another arm, corrupting the causal comparison while passing internal row SHA checks.

**RED test:** Construct a synthetic structurally consistent five-row report (never native evidence), with frozen fixture Velaris, seed 20261121, exact registered envelopes, canonical negative flags, matching recomputed raw-answer and row SHA256 and deterministic score. Swap the first two envelopes only, recompute hashes, assert `verify_report` rejects. Preserve the expected RED before source change.

**GREEN change:** Enforce `envelope.fixture_id == report.fixture_id == FIXTURE`, `envelope.seed == report.seed == SEED`, `envelope.arm == row.arm` before accepting any report; use `cf.verify_envelope` unchanged. Also reject any source-envelope verifier returning false during `_run_unlocked` preflight, before launching a native runner. No model inference in this package.

**Verification:** Run focused synthetic tests, compileall, full suite and privacy/diff scan on CI with closed original raw logs, exact head and negative gates. If CI cannot run, label unverified rather than claiming GREEN. Independent reviewer should inspect row/envelope attribution and ensure no source/seed/weight changes.

**Evidence levels:** SOFTWARE/SYNTHETIC ONLY. No native/Redmi evidence, no STEP2 or B3/JEPA promotion. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; V13 incomplete. Remaining platform budget UNKNOWN.
