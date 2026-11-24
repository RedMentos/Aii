# Run13F — explicit Age0 :jeflink operator command (2026-10-30)

Prospective review-only child of Run13E #1292 at `1ffca8c48c596db43fbffc5dba7f03b877ea53c5`. Owner GPT-6. Scope: one new `v13/jef_context_link_operator_run13f.py`, a **two-line** additive `v13/operator.py` help/dispatch entry, focused tests, dedicated CI, and scoped checkpoint. All prior JEF/ContextOS/Store/runtime native source, models, fixtures, seeds and Canon remain unchanged.

## Operator-facing utility

The user explicitly types `:jeflink <ContextPlan-Packet-ID> <QueryEvent-ID> <OldSourceEvent-ID>` at the local TTY. Only when the Runtime is idle and in Age0 RECORD_ONLY with latents OFF, jepa_weight0, stage0, and query event belonging to the currently opened session may the command call Run13E's persisted ContextPlan SOURCE_LINKS Store-bound bridge. It returns JSON containing the exact-source answer **as an operator-only diagnostic**, never inserts an assistant chat message, dispatches a tool, promotes a memory fact, triggers a model, trains weights, or changes ContextOS mode. The top-level Operator origin check already refuses non-TTY command execution; retain it. Invalid IDs and wrong-session requests must be refused without model calls.

Prospective real-Store test: create the original frozen Beacon211 budget source event, five long filler events, and a query event; run Context OS SHADOW with a low budget to produce SOURCE_LINKS pointer; invoke actual `Operator.run` with the three receipt IDs; require exact 2/2 budget values and Quartz faster, `operator_diagnostic=True`, no native, no new source rows, no assistant message insertion and all negative gates. Negative tests: malformed IDs, foreign-session query, non-TTY origin, non-Age0 config, busy Runtime and wrong packet. No automatic command in normal chat turns.

This is **narrow usable operator functionality**, not a general AI answer path, not an autonomous model output, not C5 permission, and not native full-task utility. Future active integration requires explicit user approval and a new disjoint native end-to-end preregistered test. Preserve Run13A native RED, G13 fullsuite RED, Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi unmeasured and whole-system incomplete.

CI: focused new tests, Run13E, existing operator-origin guard tests if available, Context OS baseline, py_compile, Canon, privacy/diff, original raw SHA256SUMS, private byte-exact backup. No source/seed/model/scorer hash changes.
