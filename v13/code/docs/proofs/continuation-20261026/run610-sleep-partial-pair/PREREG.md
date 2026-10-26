# Run610 — Sleep A partial-pair recovery, frozen before implementation

Date 2026-10-26 UTC. Owner: GPT automation11, review-only child of Run609 PR604 exact verified head `ef440efc0dc510ee0491fec16a88ac9991b5d905`. Run609 source-only CI 40403101157 completed SUCCESS. No native owner or model weight touched.

## Defect and prediction

In `native_history_since`, an assistant row already FINAL is selected for scanning before the shared `_validated` checks that **both** user and assistant rows are FINAL. If the matching user row is still STREAMING, `_validated` rejects the pair, but the scan advances past its assistant ID without retaining it in pending. Later user finalization cannot recover that pair: silent permanent history loss. This is distinct from revoked/invalid completed sources, which must remain excluded and allow cursor progress.

## Frozen acceptance

1. Real SQLite/Runtime: three source-valid turns; set middle **user** row STREAMING while its assistant remains FINAL; first digest includes exactly other two, records middle assistant ID in pending, and advances high-water to last assistant. On changing user status back to FINAL, second digest includes the middle turn exactly once, pending clears, chronological entries and third digest zero.
2. A pair with both rows FINAL but revoked or mismatched source is never deferred, never reintroduced, and advances cursor. A pair with assistant STREAMING retains existing Run609 behavior.
3. `native_history` latest-N output shape and source validation stay unchanged. Only `native_history_since` deferral semantics change; never accept invalid text, status or approvals. Bounded 64 valid pairs per cycle and 128 pending cap remain.
4. Run609 plus Run610 and existing Sleep/History/Context OS source-only tests; independent CI with SHA-closed raw and public privacy scan. Any failures remain RED, no fabricated native/Redmi evidence.
5. No STEP2/B3/Body-JEPA/jepa_weight/age/learning/approval promotion. `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `Redmi=UNMEASURED`, `V13=INCOMPLETE`.

Owned new proof/tests/workflow and narrow `v13/code/v13/history.py` change; no edits to Run609 branch, Canon or frozen cohorts. Next command: `cd v13/code && python -m unittest -v tests.test_run610_sleep_partial_pair tests.test_run609_sleep_digest_backlog tests.test_sleep_offline tests.test_history_lineage`.
