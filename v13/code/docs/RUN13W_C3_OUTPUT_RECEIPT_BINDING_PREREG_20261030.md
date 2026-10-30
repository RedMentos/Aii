# Run13W prereg — candidate-output receipt binding, SHADOW only (2026-10-30)

Owner: GPT-6, isolated review child of Run13V PR #1313, parent `0cd76094ac433e1b5b9e1ce05cbb57f36205d8d8`. This preregistration is committed before implementation or tests. Preserve all original Run13J/K/L/T/U native cohorts, frozen model/source/seed/scorer, Canon v10.16.1, original RED, Age0 RECORD_ONLY and negative gates.

## Concrete independent counterexample

Run13V's `_native_receipt_ok` binds model/source/prompt, but never binds **the actual candidate output bytes** to the receipt. A valid-looking receipt from one native call could be paired with a different source-fact-valid text and incorrectly labelled `C3_FACTS_VERIFIED_SHADOW`. The receipt is also an unauthenticated caller-supplied dict, so even a hash field will not independently prove native origin. The change is a *consistency guard*, not native attestation.

## Proposed change and test-first protocol

On the child branch only, extend `_native_receipt_ok` with the exact SHA256 of UTF-8 `c3_text` and its exact byte length, requiring `native_output_sha256` (lowercase 64-hex) and `native_output_bytes` (positive exact int, not bool) from a separately preserved native raw output receipt. Do not treat a missing hash/size, forged hash, wrong bytes, bool `native_calls`, or a candidate with malformed Unicode as bound. A receipt for one candidate must not authenticate a different candidate. A verified source remains eligible for **JEF source-only fallback**, never C3 success; changed/revoked source still ABSTAIN.

Use source-only real Store synthetic-receipt tests: (a) exact candidate + correct hash/size succeeds SHADOW, (b) source-valid but modified candidate with original receipt falls back, (c) missing/wrong hash/size and bool calls fall back, (d) both frozen prompt arms and wrong source, (e) source deletion and SQLite faults still abstain, (f) no native dispatch/Store writes/delivery. Preserve inherited Run13V/I/M tests. Pin and run GitHub Actions focused suite and privacy scan; capture raw evidence and hashes. A PASS is only synthetic software guard evidence, not native-output authenticity, native semantic fidelity, STEP2/B3/Body-JEPA/JEPA/Redmi or whole-system acceptance.

Owner of new files: Run13W. Existing Run13V module/test touched only on this child branch. No merge to Runtime; independent review required before any promotion. Exact next step: add test-first counterexample, observe RED, implement guard, rerun GREEN and checkpoint.