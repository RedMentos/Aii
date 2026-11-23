# Prereg: F1/F5 Memory.recall → guarded C3 source consumer (2026-10-28)

Owner GPT-6, independent software integration child of verified #883 at `43df4117b1a93d69fbb8e889fcf61c569b74afb2`. Prior #879 native heldout was 8/8 for **manually supplied** source records, not a real `Memory.recall` consumer. #883 tightened sourced value/topic boundaries (13 focused, 2282 full software PASS), but remains outside Runtime. Frozen `v13/runtime.py` Git blob `68e7ed1352800174972558f1e0b0683a42c8689a` must remain unchanged in this package.

## Proposed integration contract

Add a bounded `recall_and_admit(query, session, memory)` to the existing scoped SourceConsumer. It must obtain candidates from **actual Memory.recall** with `semantic=None`, not caller-supplied dictionaries; if no valid scoped item is retrieved, deterministically CLARIFY without a model. To prevent a low-ranked second correction from being silently excluded by top_k, independently enumerate at most 256 active exact normalized same-project budget keys (Project/Projekt × budget/budgets/etat/finanzrahmen) in the same session or explicitly global, then pass all through the existing F1/F5 source revalidation and conflict gate. Over-cap or retrieval exceptions fail closed. The enumerated rows are **conflict vetoes**, not an authority bypass: no matching retrieved record means no admission. Do not trust semantic embeddings or predicted facts as source authority.

Add `verified_recall_messages(cfg, query, session, memory)` returning `{decision, messages}`, with `messages=None` on refusal; revalidate chosen source against the store immediately before rendering. This remains an opt-in library integration candidate, **not wired into frozen Runtime**, no native/model call or learning authority.

## Frozen software checks

- Original exact source 615 Euro: Memory.recall retrieves, admission ADMITTED, rendered C3 messages cite exact user source.
- No source, wrong project, outside scope, revoked/cross-session, tampered source, malformed instruction-bearing budget and duplicate HumanDecision: no messages/model permission.
- Two active same-project budget corrections with different valid values must CLARIFY even if one would be absent from top_k/threshold.
- A global/local conflict must not arbitrarily choose a value; max 256 scoped candidates, over-cap fails closed.
- Fresh software full-suite, source pins, privacy and diff checks all GREEN before native. Preserve original 20-stage RED and previous #879 native evidence; new source requires separate preregistered native cohort.
- No STEP2, B3, Body-JEPA, LP3, Age, jepa_weight or Redmi promotion. Age0 RECORD_ONLY and source/permission authority unchanged.

**Next command:** implement opt-in library wrapper plus new adversarial tests on this separate branch; run isolated CI full software. Later, only after heavy owner releases, preregister actual Linux-native `Memory.recall`→C3 8-project EN/DE heldout with separate source/model/seed hashes and matched negative controls. No Drive anyone-writable retry.
