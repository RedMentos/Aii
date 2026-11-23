# G13/WP-V5 bounded per-dispatch retry budget — independent review 2026-10-27

**Owner:** `codex/automation11f-scheduler-retry-budget-20261027`, review-only child of PR #735 exact `db9ca7110cbcad0f03240f2ac0d60dd230c4d1c9`. PR #735 already fixes enqueue-time versus dispatch-time accounting (full suite 1900 OK); this independent package addresses two remaining distinct bypasses without changing LP3/native owners.

## Defects and fix

1. `complete(RETRY)` and retryable `CANCELLED` set an already-dispatched event back to `PENDING`. The old `background_since_input` counted only statuses `DISPATCHED/DONE/FAILED`, refunding the burn-out budget despite real work already executed. Repeated attempts of one event counted at most once.
2. Compact scheduler history retains only 64 retired events, while operator `:pause budget` can be as high as **1000**. After 65+ completed events, old dispatches fell out of history, silently undercounting the configured budget.

New `dispatch_times` ledger persists every non-USER non-notice background dispatch, including RETRY/CANCELLED attempts, bounded to **1001 timestamps** (maximum budget 1000 + 1). The ledger survives compact-history eviction and restart. Per-event `dispatch_log` is retained for review. Legacy state migration preserves known prior dispatch timestamps; attempts lost from pre-ledger compact history cannot be reconstructed and are explicitly not claimed. No change to Age/authority permissions or action allowlists.

## Verification

`tests.test_sleep_scheduler.SchedulerTests` adds two regressions: budget=2 counts each retry while PENDING, blocks third until a new accepted user turn; budget=1000 counts 70 completed dispatches despite 64-entry history. Earlier enqueue/dispatch regression remains.

Focused Actions **40529267089** exact source `ae04b0ee6366893cf9550dbf837563357bccaee5`: **8/8 PASS**, INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits all 0. Artifact `12745696175`, ZIP SHA256 `3acc1db0c664f4a6d949f5179d1f90e5c9ce518d243b9d951b2e3c847df63d13`, privately backed up and byte-verified at `/V13-Checkpoints/2026-10-27/Scheduler-Retry-Budget/scheduler-retry-focused-40529267089.zip`. Full software suite workflow `.github/workflows/scheduler-retry-fullsuite.yml` source `c98d3ca8e63fb8d2dc0b9f74d635c0218909db25` launched, result **PENDING** at checkpoint. No native/model work.

## Binding gates / next

LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; jepa_weight=0, Age authority 0, Redmi unmeasured, whole V13 incomplete. Next command: `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_sleep_scheduler.SchedulerTests`; inspect full-suite Actions and original raw exits, then independent review before integration. Do not merge to main automatically.
