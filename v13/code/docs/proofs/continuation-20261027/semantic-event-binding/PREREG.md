# WP-N8 semantic event binding — preregistered independent counterexample

Date 2026-10-27 UTC. Owner GPT-6 continuation. Review-only child of PR #743, exact parent `736a75756e8095c97b9ce738c68c2c4ae3fbde62`. This is a separate counterexample discovered during review of PR #742/#743, not an Age or semantic-quality promotion.

## Remaining gap / expected RED

PR #742 clears `SemanticKeys.last_query` whenever `Memory.recall` is invoked, but `Runtime._turn` intentionally **skips memory recall for fixed-policy responses** (`if fixed_policy: memories=[]`). `episodes.observe_turn` still accepts any `last_query` whose *text digest* matches, even if it came from a different event. Therefore an identical fixed-policy turn can consume a previous event's semantic vector despite no current embedding. Digest equality is not event identity; a cross-session same-text turn is another counterexample.

Preregister tests: (1) inject a previous-event `last_query` with matching text digest and different event ID; `observe_turn` must not forward the vector, and the snapshot must be consumed/cleared; (2) a current-event-bound vector with matching digest must still be forwarded once, then cleared; (3) `SemanticKeys.similarities` must bind its successful snapshot to the event observed at call start via an optional runtime event getter; a direct test without a current event remains non-authoritative for episode boundaries. Existing code should FAIL event mismatch and one-shot assertions.

## Proposed GREEN / boundaries

Pass a read-only current event getter from `semantic_memory.attach(runtime)` to `SemanticKeys` (optional for synthetic callers). Capture the event ID at similarity-call entry and publish it only with successful query vector. In `episodes.observe_turn`, require **event ID and text digest** to match, and consume `last_query` exactly once whether matched or not. This closes fixed-policy skip, same-text repeat and cross-session reuse without editing the frozen `runtime.py`. Preserve same-turn positive reuse, existing memory recall, source authority, and all previous cache/vector integrity guards. No model weights, native jobs, learning/age permissions or canonical gates change.

Verification: RED focused tests and exact-source GREEN, full software suite, privacy/diff/compile, closed raw evidence and private byte-exact backup. Negative gates LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, `jepa_weight=0`, Age authority 0, Redmi unmeasured, whole V13 incomplete.
