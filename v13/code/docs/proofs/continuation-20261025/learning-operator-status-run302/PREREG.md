# Run302 — :learning status must be read-only and truthful on the Phone CLI

Owner GPT-6 automation; base Run301 checkpoint `8c964d58da62fca09ae8c42a31224fcedc9e3aef` / PR #300. Owned: `v13/code/v13/operator.py`, new `v13/code/tests/test_learning_operator_status_run302.py`, `.github/workflows/run302-learning-operator-status.yml`, this proof directory. No edits to Runtime/Store, active Run297 native Context OS owner or model/seed cohorts.

## Observed usability bug
Independent extracted Run301 Phone source smoke: `:learning` with no arguments raises `ValueError: Ein Wert erforderlich`, although the binding operator requirements include a learning-status command. Users can see learning mode indirectly in `:status`, but cannot inspect `:learning` safely without knowing the configuration setter syntax.

## RED/GREEN
1. Actual production Runtime/Store SQLite and Operator: `:learning` and `:learning status` return the same JSON read-only report of actual configured mode, current Age stage and explicit approval requirement; no config file, generation, store state or learning authority changes.
2. `:learning record|shadow|commit` keeps its existing explicit setter semantics and validation; invalid multiargument values still reject without mutation. No implicit Age promotion, learning enablement or automatic approval.
3. Restart preserves configured mode; no-arg report is consistent with `:status`. Phone source ZIP extracted CLI can run the same smoke with no native models.
4. Existing operator, learning invariants, age and phone CLI regressions remain green; privacy scan CLEAN. Preserve raw RED and GREEN evidence.

Scope: software/actual SQLite, no native/Redmi learning, no STEP2/B3/Body-JEPA/jepa_weight promotion. Canon, model/source/seed hashes and frozen Runtime unchanged.
