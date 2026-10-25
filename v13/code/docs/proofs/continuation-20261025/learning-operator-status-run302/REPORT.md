# Run302 — Phone :learning read-only status: RED → GREEN

UTC 2026-10-25. Owner GPT-6. PR #301, branch `codex/learning-operator-status-run302-20261025`, base verified Run301 head `8c964d58da62fca09ae8c42a31224fcedc9e3aef`.

## User-visible implementation
Independent extracted Run301 Phone source smoke showed `:learning` (no args) raised `ValueError: Ein Wert erforderlich`. The command now supports `:learning` and `:learning status` as identical **read-only** JSON reports of the actual configured mode, current Age stage and explicit weight-commit approval requirement. It states `mode_is_not_approval=true`. Existing explicit setters `:learning record|shadow|commit` are unchanged; changing a mode does not grant an update, advance Age, or approve a model. Help text now documents the query. Frozen Runtime/Store, Canon and registered cohorts untouched.

## Closed evidence
- RED head `f88c7d9b0668c0c8f1f1bdbd5c1c36d8950f6d2f`, Actions `40204311391`, artifact `12603062058`: **45 tests, 3 errors** from no-arg/status behavior, privacy CLEAN. Preserved.
- GREEN code head `3b6c0e617a3490a8259c884535beb050ef58e995`, source blob `9e5d126040e5122e44c6808c594b591d03e356c4`, Actions `40204371994`, artifact `12602887338`: **45 tests OK**, privacy CLEAN.
- Actual production Runtime/Store SQLite and Operator, synthetic empty home. Tests verify config bytes, state row count, generation and Age unchanged by status, explicit setters still work, invalid args rejected, restart persists mode. Prior learning invariants, Age and Phone operator regressions included.
- Related Run217/Run276/Run123/Run214 and broader focused CI may still be running at checkpoint; do not infer their result.

## Claim limits / blockers
No native learning, model weight update, Redmi, STEP2/B3/Body-JEPA/jepa_weight or whole-system promotion. Separate full suite `40202886433` failed (2 failures/36 errors; frozen native candidate mismatch and cancellation cleanup), preserved under Run300 `fullsuite-run298-failure/OBSERVED.md`. No native hash relaxation.

Next: independently check related operator CI, verify a current Phone source ZIP and perform a no-model CLI smoke. Then choose next distinct canonical package without touching active Run297 native owner.
