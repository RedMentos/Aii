# Run270 preregistration — F1/F5 human correction authority in live recall

Base: PR268 exact source head `7ab557a3b9c44d4b00f9487bb70b52305a7d7c6c` (verified source-only ZIP). PR269 is a separate in-progress native workflow and must not be modified. Owner: Run270, exclusively `v13/code/v13/memory.py`, `v13/code/tests/test_memory_human_decision_lineage_run270.py` and `v13/code/docs/proofs/continuation-20261025/memory-human-decision-run270/*`. No model, native or shared status edits.

## RED observation to reproduce before production changes
`Memory._verified_rows` checks `MemoryRecord` but does not require its original `HumanDecision` and `feedback` rows. A persisted fact may still be offered to C3 after the operator-decision packet is removed or its authority/value is modified. This is a local SQLite adversarial integrity case, not a claim that an attacker can modify arbitrary files.

## Prespecified controls
1. Actual Runtime + SQLite: valid record-only and learn-permitted human correction recalls before/after restart; neither acquires training authority.
2. Delete HumanDecision packet for a correction: no lexical/learned recall of that value.
3. Change HumanDecision kind, value, source_ref, event_id, or permission to invalid: no recall.
4. Delete or falsify corresponding feedback row: no recall.
5. Change correction source kind from HUMAN_DECISION to an untrusted kind: no recall.
6. Preserve independent unaffected corrections, explicit session/global scope, and existing forget/backup tests.
7. No mutation of memory rows or source blobs on read; no authority promotion; STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, V13 INCOMPLETE.

## Procedure / stop checks
Commit this preregistration before RED. Run targeted RED test and preserve actual failure output, implement a read-only source-bound validator, rerun targeted and existing memory/consolidation/backup/restore/second-turn tests. Run available full suite if feasible and privacy scan, preserve raw logs and exact exits. Review counterexamples and remote blob readback. No Redmi or native inference claimed.
