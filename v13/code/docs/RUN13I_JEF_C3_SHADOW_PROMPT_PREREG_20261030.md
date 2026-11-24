# Run13I — verified JEF facts → bounded C3-language SHADOW prompt (preregistered 2026-10-30)

Review-only child of G15 #1297 at `bc42bb47cbd3a28b6f8b0aabf422d2bab265d5d6`, owner GPT-6. Scope: new `v13/agi/jef_c3_shadow_prompt_run13i.py` and focused tests/workflow only. This is a substantive JEF→C3 information-flow prerequisite, **not** a native model invocation, new authority, active chat route, semantic-quality proof or whole-system integration.

## Observed starting point

Run13E `propose_pointer` resolves an actual Context OS SOURCE_LINKS pointer to a Store-bound exact four-line budget/faster answer in SHADOW; Run13F/G provide opt-in local operator access. Run13H prevents SQLite read failures escaping this path. Run13A actual Linux-native C2/C3/B1/B2 full-task utility remains RED; exact deterministic JEF answers do not prove C3 can use them.

## Fixed acceptance before implementation

1. A new read-only `propose_c3_context(store, plan_id, query_event_id, source_event_id)` calls the existing Run13E proposer twice and requires both identical successful source-bound answers, SHA256 integrity, a bounded deterministic four-line answer form and exact source/query/plan identity. It creates a bounded `C3_LANGUAGE` prompt candidate containing only these verified facts, not raw untrusted source text. It must never write Store, call native models, deliver a chat turn, dispatch tools or update weights. Age0/STEP2/B3/JEPA/Redmi/whole-system gates remain negative.
2. `audit_c3_text(context, output)` is a conservative offline **exact-copy** diagnostic only: exact candidate answer may score `EXACT_COPY`, any changed/rephrased/hallucinated output scores `NOT_VERIFIED`. Neither status grants output authority. No inferred semantic correctness from partial lexical matching.
3. Real Runtime/Store/Context OS tests cover valid source pointer, no model calls, cross-session/revoked/duplicate/incorrect pointers, second-read mismatch, malformed outputs, no persisted source or assistant message mutation, and no promotion. Tests run in isolated Linux software; no native/Redmi claim. Full G14 suite historical RED stays retained, not waived.

Future experiment (not in this package): separately preregister a disjoint native C3 prompt-fidelity cohort with frozen source/model/seed and independent exact-copy + human semantic checks; no synthetic tests may promote native C3 utility.
