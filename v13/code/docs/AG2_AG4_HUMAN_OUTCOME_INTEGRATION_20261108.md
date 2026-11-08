# AG2/AG4 outcome-credit integration candidate — 2026-11-08

Owner: V13 hourly integration worker. Base: `codex/resume-20261106` at `5e964146579deb22c5ba89a2a03a52a9e4d8aab8`. Isolated branch: `codex/v13-ag2-ag4-human-outcome-20261108`. Source file: `v13/code/v13/agi/live.py`; regression: `v13/code/tests/test_agi_live_human_skill_outcome_20261108.py`.

## Real consumer path

Existing Runtime invokes `agi.live.after_turn` on completed turns, `agi.live.on_rating` for human ratings, and `agi.live.on_feedback` for corrections. Previously `after_turn` passed `status == 'FINAL'` as `SkillLibrary.record(success=True)`, automatically inflating AG4 skill utility even for incorrect answers. AG2 Grounding also records a technical FINAL status, which is **not** a semantic correctness label.

Candidate now keeps technical completion and AG2 Grounding observation, but does not credit AG4 on FINAL. A qualifying explicit human rating credits a selected AG4 route skill once per event and stores the event-bound credit marker. Repeated ratings are not double-counted for AG4; a contradictory rating marks the event disputed, not silently positive. Explicit fact corrections also mark previous positive skill credit disputed. Neutral ratings do not credit. Existing metacognition (AG9) remains on its prior path. No changes to Age, model weights, JEPA, registered cohorts, tools or native runner.

## Known limitations / not promoted

- **Crash atomicity OPEN**: AG4 aggregate increment and per-event marker currently use separate Store writes; a crash between them may double-credit on retry. Must implement a transaction-bound event ledger and rebuild/retraction before any active AG4 learning authority.
- **Correction rollback OPEN**: disputed AG4 historical counts are flagged, not retracted. Current candidate is non-promoting, not evidence of corrected aggregate utility.
- Existing AG9 Metacognition repeated rating behavior is not deduplicated by this change.
- SourceHandoff frozen runtime: this is a review-only candidate, not integrated into the registered cohort.
- Tests authored but **not executed on exact checkout** because direct git clone failed DNS; do not claim passing tests. No native/Redmi/learning-utility proof. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, jepa_weight=0 and full-suite RED remain unchanged.

## Verification and next work

Remote source and test files read back; exact commit hashes in PR. Test command from repo root: `cd v13/code && python -m unittest discover -s tests -p 'test_agi_live_human_skill_outcome_20261108.py' -v`. Then run adjacent AG2/AG4/AG9 and Runtime tests. Independent review of rating correction, crash-window and skill promotion semantics. Build an atomic, source-bound event ledger and reconstruct AG4 statistics before activating. Run `python v13/code/scripts/public_repo_privacy_scan.py --base <verified base> --head <candidate>` on a real checkout and full integration tests. Then return to multi-path experience→association/attention/replay integration. No unapproved self-modification.
