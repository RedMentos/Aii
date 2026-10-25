# Run289 — atomic update-row identity at learned generation approval

Date: 2026-10-25 UTC. Independent owner: `v13/code/v13/store.py`, `tests/test_atomic_update_approval_row_run289.py`, dedicated CI and this scoped proof. Base: Run288 PR #288 `be4e39e33c99e36c889dab892bf2367a0f3fcfdc`. This is branch-scoped and not production-integrated.

## Concrete defect and repair

`Store.switch_generation` preflighted an update before `BEGIN IMMEDIATE`, then checked only the active generation and old source IDs inside the write transaction. A second Store thread could revoke the candidate, lower its retention gate, change its source lineage or swap its checkpoint pointer before approval; stale preflight data was committed anyway. Run289 re-reads `status,base_generation,path,hash,manifest` inside the **same SQLite write transaction** and rejects missing/revoked/changed rows before any generation mutation. Existing source-revocation and retention gates remain unchanged. No new learning authority.

Official primary references, checked 2026-10-25: https://www.sqlite.org/isolation.html (one writer, snapshot/transaction isolation); https://www.sqlite.org/lang_transaction.html (`BEGIN IMMEDIATE` write transaction). Scope: SQLite row identity; external filesystem races remain separately unproven.

## Closed RED -> GREEN evidence

- RED exact head `90d0153d4ac226456f233000cddda740e6e79927`; workflow `40195820189`; **55 tests: 4 FAIL / 51 PASS**, all four new race counterexamples failed because ValueError was not raised; unchanged commit/rollback positive control passed. Official privacy scan CLEAN. Raw Actions artifact `12600280476`, archive SHA256 `03583a25c187e57015307917f0e8adf12d307889860afa58adb910251c6e7336` (GitHub artifact digest).
- GREEN exact source head `a4cd4df0b95a5faf4163d8e5c1d2f05862c31efe`; workflow `40195901481`; **55/55 PASS**, four adversarial mutations rejected, unchanged commit/rollback passed. Official privacy CLEAN. Raw Actions artifact `12599464840`, archive SHA256 `5e31c10f1990b899b65e10ce81f33d8cea34b5727cdb8668c92213b1120e0a8f`.
- Same source head Run287 regression `40195901503` SUCCESS and persistent multichat journey `40195901513` SUCCESS.
- Focused PR-merge checkout `40195901521`: 401/401 software tests PASS, extracted Phone source 114/114 PASS and restart PASS; official privacy CLEAN. Independently verified phone ZIP 1001 source files, SHA256 `c69934326b9b85e8dd9c1d7c647f40a054e2e1fce0f4b49b79045b401cc3a287`, 12,909,355 bytes. Workflow artifact `12599569381` SHA256 `b652f599ab852f02bf7be60ad2aaee1cca8dd845de4e9cf9779689941d98dc52`. The focused workflow uses the PR merge checkout, unlike dedicated exact-head Run289.

## Hash binding / evidence classes

- Canon SHA256 `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee` unchanged.
- `v13/code/v13/store.py` Git blob `75f91eedd0d70d4244e80d61409b07b27fa5abd3` (prior `4fa1d8858412d739ffddb3509d711e4523cb2c0b`).
- `v13/code/tests/test_atomic_update_approval_row_run289.py` Git blob `35d792f4332b2e6c8202dc1cff569f4ba2466ec4`.
- `.github/workflows/run289-atomic-update-row.yml` Git blob `a172e8c314b594fce18775a8991f88293c94487a`.
- Evidence: Linux/SQLite software with synthetic candidate bytes; **not** actual model-weight learning, Redmi, or full native acceptance.

## Original negative gates / remaining questions

`STEP2=UTILITY_FAIL`, `B3 L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `jepa_weight=0`, `V13=INCOMPLETE`, `redmi_measured=false`. PR284 Runtime cancellation remains separately owned/RED until native evidence. Run288 full 20-stage pinned-native acceptance is independently running on its unchanged base and must be reviewed before any gate promotion. External artifact mutation and true simultaneous filesystem tampering are not proven safe by this SQLite test.

**Next concrete independent package:** Inspect `Memory._forget_source` for generation changes between its preflight active-weight check and its deletion transaction. Reproduce the counterexample against actual SQLite Store and fix only if RED, without modifying PR284 Runtime or Run288 native owner. Continue substantive native utility fixes once Run288 raw failures are available. No rejected anyone-writable Drive destination was used.
