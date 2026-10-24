# Run102 — User non-disclosure prohibitions must cover SEND, not just CONTACT (preregistered)
Date: 2026-10-25 UTC. Base verified Run101 PR #133 head `71d2fcbdda23d7cc68ad4e5c50915d9eb5074227`.
Owner: `v13/code/v13/userrules.py` ACTION_STEMS['SEND'] only; new `tests/test_userrules_nondisclosure_run102.py`, isolated workflow and this proof. Do not touch Run99 Callosum, Run97 JEF, Run96 Sleep, Run94 World Model, Run100 Context OS or Run101 ToolStep.

## User binding
Explicit 2026-10-21 user decision: no action unknown to user; no misreading "please don't"; fixed non-generative rule reader, no model rule interpretation. Tool actions remain gated and user-visible. This package closes a concrete **fail-open** fixed-lexicon hole, not a change to Age or tool permissions.

## Reproduced failure hypothesis
`Do not expose my phone number` currently yields FORBID actions `CONTACT` only because the object `phone number` implies CONTACT, while the verb `expose` is unrecognized. A declared `SEND` action with `CONTACTS` payload can therefore be `ALLOW`, despite the user's prohibition. Same for `reveal`, `divulge`, `broadcast`. Existing `disclose`, `share`, `publish` are recognized.

## Preregistered tests (real Runtime/SQLite rule persistence, deterministic declared effects)
Create actual user-typed rules with `U.add(store,...,'USER_TYPED')`, re-read persisted `U.rules(store)`; compare a **synthetic declared SEND effect** `{actions: SEND,TOOL; objects: CONTACTS,CONTENT_ANY,TOOLS; declared: true}` through the production `U.verdict` function. Four negative cases:
1. `Do not expose my phone number.` => DENY (expected RED now).
2. `Do not reveal my phone number.` => DENY (RED).
3. `Do not divulge my phone number.` => DENY (RED).
4. `Do not broadcast my phone number.` => DENY (RED).

Positive controls: `Do not disclose my phone number.` => DENY; `Keep my messages private.` => ASK (not silent allow); `Please reveal my phone number.` => no prohibition; and an unrelated calculator effect remains ALLOW. The SEND effect is a **synthetic policy fixture**, not an actual message or external network call. Restart/persistence and existing G1–G6 tests remain required.

Candidate: add only unrecognized disclosure stems `expos`, `reveal`, `divulg`, `broadcast` to SEND. No model, no external tool execution, no loosening of rules. Preserve RED and intermediate failures. Run official public-repo privacy scan. Existing STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE; no gate promotion.
