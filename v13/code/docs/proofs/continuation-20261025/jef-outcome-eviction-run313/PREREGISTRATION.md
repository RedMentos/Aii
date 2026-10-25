# Run313 preregistration — JEF self-outcome label identity survives bounded retention

2026-10-25. Owner `assistant/jef-outcome-eviction-run313-20261025`.
Exact parent `f97266161647692af204043661eab09bb1b10dbf` (Run312 review branch; production main not updated).
Owned files only `v13/code/v13/jefoutcome.py`, `v13/code/tests/test_jef_outcome_eviction_run313.py`, this proof directory and dedicated `.github/workflows/run313-jef-outcome-eviction.yml`. Do not modify Runtime, Store, FastForward, Canon, model/seed/cohort or shared handoff.

## Observed code path and RED hypothesis
`jefoutcome.after_turn` remembers processed (event,component) only in the last `MAX=1024` labels. After eviction, replay of a historical FINAL event may allocate another `OUTCOME_SELF_LABEL` source and append a fresh self-label; if the derived target changes, it can even relabel that event. Existing same-event test only checks within the retained window. A race between concurrent callbacks may allocate unused authority-typed sources before the CAS recheck.

## Frozen acceptance
1. Under a test-only small MAX=2 (same code path as 1024), three real Runtime/Store SQLite FINAL events evict the first; replaying the first after restart must create no new self-label/source and must not evict another label.
2. A changed derived target on an evicted event must not re-label it or create an authority source.
3. Two concurrent callbacks for one event must produce exactly one label and one source (no orphan on the normal concurrent path).
4. Distinct events/components still record, remain source-bound, and old JEF outcome/human-veto/route-correction tests pass.
5. Persistent per-event/component receipts in existing SQLite `states` table; no schema change. Serialize source creation with Store mutex; receipt + bounded ledger update share one SQLite transaction. An OS crash between immutable source creation and ledger commit can leave an unreferenced source row (fail-closed, not an active self-label); no claim of a full cross-filesystem atomic transaction.
6. No self-label training in `record` mode, no extra authority or gate promotion.

## Proof plan
Commit preregistration, RED tests and exact-head dedicated CPU CI first. Preserve raw failing attempts and hashes. Patch only JEF module, run focused real SQLite JEF tests, official privacy scan and independent review. Keep Run310 full-suite negatives and original STEP2/B3/Body-JEPA/Redmi/jepa_weight gates unchanged. This is software-only.
