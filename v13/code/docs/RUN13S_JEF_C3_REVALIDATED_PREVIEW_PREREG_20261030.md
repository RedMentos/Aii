# Run13S — source-revalidated JEF→C3 shadow preview with exact fallback (2026-10-30)

Owner GPT-6, review-only child of Run13R PR #1309. **This preregistration precedes implementation.** No Runtime/Operator/Store native egress integration and no changes to frozen Run13J/K/L model/source/seed/scorer cohorts.

## Need and scope

Run13L actual native C3 exact literal copy was 0/6 despite source-verified JEF context; Run13M introduced a deterministic grammar fidelity audit (20/20 software tests), but no end-to-end source-revalidation/fallback consumer. New candidate composes the *existing* real Store source lineage with C3 candidate and the Run13M audit into one explicit operator-only preview. The JEF answer is deterministic source-derived text; fallback does **not** count as C3 model success, semantic generalization or Body-JEPA learning.

## Fixed behavior

- Input: Store, exact `context_plan_packet_id`, `query_event_id`, `source_event_id`, pre-native Run13I `linked` witness, a native C3 text candidate, native status, process-reaped flag, role and call count. No model invocation inside candidate.
- Require `prompt_for(linked, "COPY_DIRECT")` source/hash/authority checks before any preview; require strict native role `C3_LANGUAGE`, exactly one completed `FINAL` call and process reaped. Incomplete/error/unreaped/non-text native candidates yield `ABSTAIN_NATIVE_RED` with no preview.
- After native completion, call `propose_c3_context(store, plan_id, query_id, source_id)` afresh (which re-reads the real Store twice). Require a second valid `prompt_for` and identical source event IDs, plan/query IDs, answer SHA, prompt SHA and answer bytes between before/after. Revoked, missing, changed, corrupted, wrong-session or SQLite-faulted source yields `ABSTAIN_SOURCE_RED`, no preview; never use a stale pre-native answer as fallback.
- Run `audit_source_facts(after, native_text)` (Run13M). If all source facts match exactly, return `MODEL_VERIFIED_PREVIEW` with native text. Otherwise return `SOURCE_EXACT_FALLBACK_PREVIEW` with the *fresh* source-derived JEF answer. Preserve the original model failure reason and native candidate SHA, do not relabel fallback as model success.
- Both success statuses are `SHADOW_NO_AUTHORITY`, `operator_only=true`, `no_autonomous_egress=true`, `delivery_authority=0`, `context_authority=0`, `weight_updates=false`, Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, runtime jepa_weight0, Redmi unmeasured, whole-system incomplete. The candidate does not write chat messages, create HumanDecision approvals, call native models or enable learning.
- Predeclared tests: real Store positive exact, wrong numeric/faster/extra text fallback, source deletion/supersession/changed query, SQLite read exception, native wrong role/unreaped/nonfinal/nontext, no extra Store messages/sources, no model pool calls; regression against Run13I/M tests. No user-facing active delivery. Later native end-to-end proof is separate and must be preregistered before any new native cohort.
- No performance/quality promotion from deterministic fallback. If the C3 model fails all six outputs, a 6/6 source-exact preview is **0/6 C3 success**; both numbers must be reported separately.

**Freeze and owner:** Runtime Python remains frozen for SourceHandoff; new code lives in a separate `v13/agi` SHADOW module, no existing runtime edits. GitHub review only, full original raw and private backup, no force-push or Drive approval bypass.