# Run84 prereg — exact operator rule approval/rejection lifecycle (2026-10-28)

Owner GPT-6 scheduled continuation. Independent review-only sibling of Run82/83, based on independently raw-verified Run76 #983 GREEN head `2fa443822f99b367d137f0254e69e20268f664e8`. Scope: real Linux Runtime/Store/Operator in a fresh temporary home, no native models, no user data, no production source modifications.

## Frozen plan before implementation

1. Real Runtime with Sleep disabled, learning RECORD_ONLY; capture current rules and rule version. Propose a free-text `:rules add ...`, verify it creates a PENDING request but active rules and generation do **not** change. Reject the exact request ID; active rules remain unchanged after restart.
2. Propose typed exact `:rules fixed "What is two plus two?" "4"`. Verify it is **not** active before explicit `:approve <exact ID>`; invalid ID approval refused. Approve exact ID; require a changed rule version and `output_policy.match(store, "What is two plus two?")` returns exact `4`, `model_generated=false`, `output_authority=APPROVED_FIXED_RULE`. Near-match question must return None (no fuzzy matching).
3. Restart real Runtime, require the exact rule still active, learning RECORD_ONLY. Propose `:rules remove <index>`; active rule stays until exact approval. Approve removal; match becomes None. Restart again, verify removal persists and old rejected proposal never activated.
4. Patch native runner pool access to raise on any attempted call; this entire test uses only source-backed fixed rule machinery, no B/C models. Do not call `:learning commit`, grant tool rights, promote Age or alter any production source.
5. CI: source-bound focused new E2E + output_policy/age/rule tests, full software suite, privacy, closed raw SHA256SUMS. Preserve RED. This proves operator rule approval lifecycle only; not C3/B1/B2 quality, native/Redmi, STEP2/B3/Body-JEPA/LP3 or whole-system completion.

No change to existing rule thresholds, matcher semantics, generation ownership, or historical cohorts. Next after GREEN: independently review operator/approval source lineage and run native/Redmi acceptance separately.
