# Run345 prereg — C5 pre-dispatch ActionIntent/CorollaryCopy/action atomicity (2026-10-25)

Base: verified Run344 checkpoint `83f64ee7304e9808d2abc976a5da3fcb7a44a5e2`, including Run343/342/340. Owner: only `v13/code/v13/store.py` and new Run345 tests/workflow/proofs. No edits to frozen SourceHandoff Runtime, Canon, native model/cohort hashes, age/approval rights or active Run339 experiment.

## Concrete source defect
`Store.start_action` writes ActionIntent packet, CorollaryCopy packet, then actions row in **three separate SQLite transactions**. A crash, packet validation error, or SQL INSERT failure between them can persist a claimed intent/corollary without the corresponding dispatched action, or one without the other. This breaks pre-dispatch action lineage and creates misleading C5/World evidence. The existing `finish_action` path was hardened in Run344; this is its upstream creation counterpart.

## Predeclared acceptance
- Production Runtime/Store SQLite, one real EventEnvelope; synthetic local action intent, no model/tool execution.
- Inject actions-table INSERT failure after intent+corollary are constructed. Neither packet nor action may survive; original RED should show two orphan packets.
- Inject CorollaryCopy packet INSERT failure after intent construction. Neither packet may survive; original RED should show one orphan intent.
- Successful start commits exactly one ActionIntent, one CorollaryCopy and one DISPATCHED action with the same action ID, event, generation and expected payload; WorldState can subsequently observe a finished outcome without changing source authority.
- Unknown event ID and mismatched event generation must fail closed with zero packets/action rows.
- Two distinct concurrent starts retain distinct action IDs and their own packet bindings; restart keeps exact persisted provenance.
- RED-first tests, minimal single-transaction implementation, exact-head focused regression CI, privacy scan, closed raw SHA, private Library backup and independent review. No new external permission, no action execution, no STEP2/B3/Body-JEPA/Redmi/V13 gate promotion.

Next: add tests/workflow; preserve RED; then implement atomic start_action and verify.
