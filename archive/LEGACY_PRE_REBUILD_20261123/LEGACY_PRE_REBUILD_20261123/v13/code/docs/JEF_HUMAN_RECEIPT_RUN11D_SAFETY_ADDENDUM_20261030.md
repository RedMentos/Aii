# JEF receipt run11d — safety addendum before final repair (2026-10-30)

The initial prereg and RED test set (Actions `41018948224`, 7/20 failures) assumed that a malformed human receipt should be treated as **no human correction** and therefore allow lower-authority self-outcome training. Independent review of the authority hierarchy found that this would weaken containment: a corrupted human packet could remove a real human veto. The intermediate code at `7257dcbf5a16d796f8e8ba35f5bf3e98f4f78b27` passed those initial tests but is **NOT the final safety policy** and must not be promoted or integrated as-is.

Revised, more conservative requirement **before final implementation**:
1. An invalid/stale/substituted human receipt must **never** be admitted as a *valid explicit-human training label* (source kind, value, permission, event, decision, source hash/span and bytes must all match).
2. An active human feedback row still associated with a matching decision/context remains a **conservative veto** against lower-authority self-label training even when its receipt is malformed. Fail closed: neither forged human training nor self-training may exploit corruption.
3. Explicitly deleted/revoked human sources are no longer active human vetoes, matching existing source revocation semantics; never revive a tombstoned source.
4. Existing genuine human RECORD (including older than 512 recent feedback) continues to veto. Age0 default remains RECORD_ONLY.
5. Adjust tests to assert the two distinct questions separately: `_valid_human_receipt=False` for corruption and `training_rows=[]` while active suspect feedback exists; verify the learning caller does not classify a forged receipt as valid human training.

The original RED raw and intermediate GREEN raw remain immutable historical evidence; the revised test contract is not falsely called preregistered before those observations. No native/Redmi/STEP2/B3/JEPA or age gate changes.
