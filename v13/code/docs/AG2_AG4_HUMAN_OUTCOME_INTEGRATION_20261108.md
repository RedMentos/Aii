# AG2/AG4 outcome-credit integration candidate — 2026-11-08

**Review update:** On a separate child of #1611, the exact original tests were run, five behavioral counterexamples were reproduced, and 97 targeted/adjacent tests passed after repairs. The original #1611 Actions result remains RED. Read `AG2_AG4_HUMAN_OUTCOME_REVIEW_20261108.md` for the updated scope and unresolved source, AG9, historical and shadow-parity limitations; the following text records the earlier candidate state.

Owner: V13 hourly integration worker. Base: `codex/resume-20261106` at `5e964146579deb22c5ba89a2a03a52a9e4d8aab8`. Isolated branch: `codex/v13-ag2-ag4-human-outcome-20261108`. Source file: `v13/code/v13/agi/live.py`; regression: `v13/code/tests/test_agi_live_human_skill_outcome_20261108.py`.

## Real consumer path

Existing Runtime invokes `agi.live.after_turn` on completed turns, `agi.live.on_rating` for human ratings, and `agi.live.on_feedback` for corrections. Previously `after_turn` passed `status == 'FINAL'` as `SkillLibrary.record(success=True)`, automatically inflating AG4 skill utility even for incorrect answers. AG2 Grounding also records a technical FINAL status, which is **not** a semantic correctness label.

Candidate now keeps technical completion and AG2 Grounding observation, but does not credit AG4 on FINAL. A qualifying explicit human rating credits a selected AG4 route skill through an atomic event-bound ledger in the same versioned AG4 state as its aggregate counters. Repeated ratings are idempotent, including across restarts or a crash before the auxiliary live marker is written. Contradictory ratings and explicit fact corrections replace the old success label and retract the AG4 success counter; the event remains one use. Corrections are marked for review, not used as proof of model improvement. Neutral ratings do not credit. AG9 now receives repeated human rating labels through its existing atomic receipt-deduplicating batch API, reducing duplicate calibration labels. No changes to Age, model weights, JEPA, registered cohorts, tools or native runner.

## Known limitations / not promoted

- **Historical migration OPEN**: AG4's preexisting aggregate counters can contain technical-FINAL successes. New event-bound ledger corrects only its own entries; historical counts need evidence-bound migration/rebuild before promotion or trust claims.
- **Correction and stage rollback OPEN**: new event credits retract counters, but a historical stage promotion based on contaminated aggregate evidence is not automatically reversed. Human review is required.
- **Ledger bounds OPEN**: 4096 event receipts per Store; capacity exhaustion rejects new credit rather than silently forgetting deduplication.
- AG9 repeated rating receipts now use its existing atomic batch deduplication (last 256 receipts per component); corrected ratings still require a retractable calibration ledger and are not retroactively repaired.
- SourceHandoff frozen runtime: this is a review-only candidate, not integrated into the registered cohort.
- Nine regression tests authored but **not executed on exact checkout** because direct git clone failed DNS; do not claim passing tests. No native/Redmi/learning-utility proof. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, jepa_weight=0 and full-suite RED remain unchanged.

## Verification and next work

Remote source and test files read back; exact commit hashes in PR. Test command from repo root: `cd v13/code && python -m unittest discover -s tests -p 'test_agi_live_human_skill_outcome_20261108.py' -v`. Then run adjacent AG2/AG4/AG9 and Runtime tests. Independent review of rating correction, crash-window and skill promotion semantics. Rebuild historical AG4 counters from source-bound events, review stage transitions and add durable ledger archive/compaction before activating. Run `python v13/code/scripts/public_repo_privacy_scan.py --base <verified base> --head <candidate>` on a real checkout and full integration tests. Then return to multi-path experience→association/attention/replay integration. No unapproved self-modification.
