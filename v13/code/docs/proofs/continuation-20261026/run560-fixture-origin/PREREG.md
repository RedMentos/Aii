# Run560 prereg — frozen fixture-origin binding and independent Run557 FUTURE_002 offline audit

Date: 2026-10-26. Base: Run559 PR #558 exact head `1f2d911bf1a7e80f8680f3692f96e7b97cb6a258`; Run559 exact-head source CI `40352509999` SUCCESS. Run557 original serialized Linux-native Actions `40350723259` SUCCESS at `5cbf54f8c8ff2fe3fb8531a76a560493c7041296`. This is a new source-only review branch, not a main merge. All registered source/model/runner/seed hashes remain unchanged.

## Finding before edits

Run559's independent scorer obtains the oracle from `step2_<arm>_s<seed>.json['fixtures']`, a native-run output. It checks `step['fixture_sha256']` against the frozen stage but does **not** independently compare the embedded fixture objects (including oracle and history) to the immutable Run491 original source. A self-consistent mutated oracle and recomputed utility in a rehashed artifact could be misclassified as independently grounded. The original artifact ZIP SHA pins still protect an *already pinned* archive; the missing source-origin comparison matters for newly supplied artifacts and future batches.

## Change / acceptance

1. In `run559_offline_review.py`, reconstruct each exact two-fixture stage from `run491_step2_heldout10.registration()['fixtures']`, require its canonical SHA to equal frozen stage SHA, and compare the entire native-recorded fixture list exactly (including order, oracle, history, options, rules, current). Only use **source-frozen** oracles for the independent 12-field score. Fail closed on tampered oracles, history, swapped order, missing or duplicate fixture; do not alter any original Run491/500/504 registration.
2. Add model-free adversarial tests with a positive original fixture pair and mutations to oracle values, history and order.
3. Independent source-only Actions at exact head: run new tests and existing Run559/Run558 source tests, SHA-close raw including RED, privacy scan. Download **original immutable** Run557 raw artifact id `12664912862`, SHA256 `ae44a8d97b0a0d1e658a91fc2c7731fe5854592a9dbfe5cfe173a6cc80b9419b`, and safe artifact id `12665895129`, SHA256 `ecd1ece00a2e82396bbd716b4fab93c84efe81ce60d9e853b8b450a437d4eb03`. Require the exact `RUN557` Actions head and `FUTURE_002`; run independent Run559 auditor against original bytes, preserve raw and report even on RED. No native execution, model download, or paid provisioning. Treat any failure as a finding, not a reason to relax pins.
4. Verify remote commit and workflow evidence. Record actual observed means, zero wrong committed if confirmed, and unchanged STEP2/B3/Body-JEPA/Redmi negative gates. No completion or learned-utility promotion.

## Scope and ownership

This package owns only `v13/code/scripts/run559_offline_review.py`, `v13/code/tests/test_run560_fixture_origin.py`, this new Run560 proof directory, and `.github/workflows/run560-native002-offline.yml`. No shared BUILD_STATE/ROADMAP rewrite in this package; new proof checkpoint records exact next command and blockers. Run557 original ZIPs are read-only. Native jobs remain serialized and outside this package.
