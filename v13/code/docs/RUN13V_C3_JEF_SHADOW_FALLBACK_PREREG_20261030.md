# Run13V — preregistered source-bound C3/JEF fallback mux, SHADOW only (2026-10-30)

Owner GPT-6; review-only child of independent Run13U PR #1312 at `64d491f40dcd1b554bdeed6b62fc465ee6c7490d`. This preregistration precedes implementation/tests. Preserve entire Canon v10.16.1, frozen Run13I/J/K/L/M/T/U source, original native raw, scores, model pins, seeds, and all negative gates.

## Motivation / exact candidate

New Run13T original Linux-native disjoint 16-call C3 system ablation was structurally GREEN but `FIDELITY_HURT`: **0/8 byte-exact copies in either arm**, strict-full baseline 6/8 vs stricter 4/8, source-facts verified baseline 3/8 vs stricter 0/8. Do not claim the small C3 reliably reproduces JEF verified facts. The next safe path is a deterministic **SHADOW-only selection policy** that preserves the already verified JEF answer when the C3 text fails exact source-fact validation, rather than forcing the model to invent a faithful copy.

Candidate `v13/agi/jef_c3_shadow_fallback_run13v.py`:
- Inputs: read-only Store, exact ContextOS plan/query/source IDs, original `propose_c3_context` snapshot, optional C3 candidate text and native receipt.
- Recompute `propose_c3_context(store, plan_id, query_id, source_id)` at selection time. Require full snapshot equality, verified source and hash/size/authority invariants; otherwise **ABSTAIN** with no text. This is a best-effort SHADOW recheck, **not** atomic production egress authority.
- If source is still valid but C3 output or native receipt is missing, stale, malformed, not FINAL/reaped, wrong role/model/source/prompt, oversized, or source-facts validator rejects it, select **exact verified JEF answer** as `JEF_VERIFIED_FALLBACK_SHADOW`. Do not present it as a successful C3 answer.
- Only when source is revalidated, native receipt is fully bound and `audit_source_facts` returns `FACTS_EXACT`, select candidate C3 text as `C3_FACTS_VERIFIED_SHADOW`. All selected texts remain operator-only, no automatic delivery.
- Receipt must bind C3_LANGUAGE, one FINAL/reaped call, positive PID, pinned 350M GGUF SHA/revision, exact source/query/plan IDs, verified answer hash, and one of two frozen source-derived prompt hashes: Run13I JEF prompt or Run13K COPY_DIRECT prompt.
- Outputs include explicit reason, selected-text SHA256, provenance, no autonomous egress, zero *mux* native calls/writes/learning, delivery/context authority0, Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi unmeasured, whole-system incomplete.
- Fail closed on malformed input, source read/SQLite errors, snapshot changes, revoked/deleted sources, and output encoding errors. No new active Runtime route, Store write, model dispatch, C3 training, JEF authority, Dream/Sleep change or user-visible delivery.

## Required tests and limits

Source-only tests against a real Store/Runtime, synthetic verified JEF cases, native-call monkeypatch refusal, no assistant messages or writes, valid C3 source-fact paraphrase, malformed/forged receipt, wrong faster/amount, source snapshot mismatch, revoked/changed source, oversized output, nontext output and no promotion. Independently run original Run13I and Run13M tests. Publish review-only branch with raw CI hashes and private backup. No native job; original Run13T native remains frozen and negative.

This candidate **cannot** prove useful C3 language modeling: fallback correctness derives from deterministic JEF source computation, not C3 inference. Even a passing test does not promote STEP2, B3, Body-JEPA, JEPA learning, Redmi or whole-system completion. Original 4027-test full suite historical RED remains.
