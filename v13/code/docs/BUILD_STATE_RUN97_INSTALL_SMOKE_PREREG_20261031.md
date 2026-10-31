# Run97 preregistration — bounded first-install smoke (2026-10-31)

Owner: GPT-6 automation continuation. Review-only child of Run96 PR #1462, exact parent `2f9ad42c1c448c4f08f2319e03770de996816626`. Branch `assistant/v13-run97-installer-smoke-20261031-auto11`. This preregistration must precede implementation and execution. Source `v13/code/setup.sh` blob `e7302f9e2ce74b6c98bea4df604552993ca44340`; unfiltered `v13 selftest` in `v13/code/v13/__main__.py` blob `9248e46e199a4227c296d538e6a2ef969e8e10cb`.

## Observed original failure and scope
Run96 original Linux minimal-deps installer diagnostic Actions 41200809286: collector SUCCESS, original unfiltered selftest **exit 124 (90s timeout)** while still running, no completed test count. Original ZIP 13042925787 SHA256 `ac9d72556ee3e249f59bbc3f4521935dc818e35e4eadf1949361d66b5c0fe2a9`, CRC and 17/17 inner hashes checked; private backup already confirmed. Separate fully provisioned Run94 unfiltered suite 4907 OK, 28 skipped, 461.260s. This does not establish missing dependency or Redmi behavior.

## Planned isolated package
1. New `v13/code/scripts/install_selftest.py`: a fixed exact allowlist of real existing age/Store/Runtime queue/standstill/SourceHandoff tests; no `discover` wildcard, no model downloads, no native inference, explicit model-free scope. Worker run in separate process with a 120s wall-clock timeout and fail-closed import/missing-test/count/error handling; terminate worker process group on timeout.
2. Update **only** installer invocation in `v13/code/setup.sh` to call this bounded smoke after bootstrap. Leave `v13 selftest` full developer discovery unchanged, and leave original native `v13 probe` after smoke.
3. Add isolated unit tests for runner allowlist, empty/unknown test refusal, and timeout; Linux CI with fresh venv and setup's explicit Python deps (numpy and prompt-toolkit), no models. Capture original raw stdout/stderr, exit codes, exact HEAD, pip freeze, shell/compile/privacy/diff receipts and closed SHA256SUMS in GitHub Actions artifact. Preserve any RED.
4. If GREEN, build a **new** phone source ZIP in a separate follow-up package; do not overwrite Run95 source ZIP. A Linux CI pass is not a Redmi install proof.

## Immutable limits
No edits to frozen `v13/code/v13/` Runtime/Store, Canon, original evidence, registered source/model/seed/cohort, native ownership, age rights or approvals. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight=0; Redmi UNMEASURED; whole V13 INCOMPLETE. Draft PR, no production merge or force push.
