# Run610 — Sleep A partial user-pair finality recovery

Recorded 2026-10-26 UTC. Review-only child of Run609 PR604 exact verified head `ef440efc0dc510ee0491fec16a88ac9991b5d905`. Parent Run609 real SQLite source CI 40403101157 SUCCESS. Current owner: GPT automation11. No native/model owner acquired.

## Source change

`v13/code/v13/history.py` now defers an assistant ID if its row is FINAL but its **paired user row is not FINAL**. Previously the shared source validator correctly rejected the pair, but the oldest-first high-water scan advanced and silently discarded it forever. The fix only retains a bounded assistant ID for later source revalidation; it does not accept unfinalized text or source, and revoked fully FINAL sources are still excluded rather than deferred. Original latest-N `native_history` remains untouched. No changes to model weights, learning rights, Age or approval.

Prereg before code: `1916a8a59bb3bad3ecfcd252401f91ecc6721493`; failing-case test introduced before code at `b9d005f3cc4c14bfacefce1f393e46235acf51f9` (pre-fix execution was **not** observed; do not claim an actual RED run). Source fix `4ecd8ebe23d9d213bff4da49eb37dcc78b674d52`; inherited Run609 CI child-branch extension `522906bbf8001bbed00aef64eb87967e72fa919d`. The new standalone Run610 workflow file was committed but did not independently trigger; actual execution used the inherited Run609 workflow with the Run610 test and privacy base updated to PR604.

## Closed evidence

- GitHub Actions source-bound `40404858588`, exact head `522906bbf8001bbed00aef64eb87967e72fa919d`, **SUCCESS**. Actual Linux SQLite/Runtime tests: **68 tests, 70.955 s, OK**, including both new tests, all Run609 backlog tests and existing Sleep/Context OS regressions. Public privacy scan: **CLEAN**, exit 0.
- Artifact `12691690663`: outer ZIP SHA256 `cf52f5b74e0f143ee08fac951bf8d43cde2d7307d48ec418600118ef68cacbf6`, matches GitHub digest. Independent local rehash of **all 7** entries in `RUN609_SHA256SUMS.txt` matched. Source SHA256 `history.py=a10ec3290b004802cbb6838ea760cad52816271d618506c014376660f80ab10f`, `test_run610_sleep_partial_pair.py=db506408f48c6b619f45d81e8c97b8d62f0f9e51de44dae522cc9b001b1194c4`.
- Independent read-only Run608 native artifact audit posted on PR603 (comment 6427835427): outer SHA, 15/15 manifest, 80×2048 B1 and 80×1024 B2 finite states, negative conclusion preserved. This is an artifact audit, not a new native inference run or B3 promotion.

## Boundaries and next work

This is a Linux software/SQLite fix, not native performance or Redmi proof. STEP2=UTILITY_FAIL; B3_L1=FAIL; Body_JEPA=UNAVAILABLE; jepa_weight=0; Redmi=UNMEASURED; V13=INCOMPLETE; canonical/user full scope false. The bounded 128 pending-ID fail-closed limit remains; prolonged unfinalized records beyond that bound are a separately open operational condition. No evidence of pre-fix CI RED is claimed. Run596 unfiltered fullsuite inherited RED is not reclassified.

Exact reproduction from repo root:
`cd v13/code && PYTHONPATH="$PWD" python -m unittest -v tests.test_run610_sleep_partial_pair tests.test_run609_sleep_digest_backlog tests.test_sleep_offline tests.test_history_lineage tests.test_context_os tests.test_sleep_scheduler tests.test_sleep_validation`

Next: verify PR605 head and CI remote bytes; independent code review for partial-user status transitions and current parent; continue next *different* canonical functional package (user-facing Context OS/Sleep backlog observability or another roadmap organ) rather than stopping after this checkpoint. Do not compete with native owners. Source/checkpoint remain review-branch-scoped; no production merge implied.
