# Run271 preregistration — ContextOS warm memory must not bypass F1/F5 authority

Base: PR270 verified remote checkpoint `33092440a9e719ce17b120f36e211ccdfad077bf` (PR270 CI pending). Disjoint owner: Run271 owns only `v13/code/v13/context_os.py`, `v13/code/tests/test_context_warm_authority_run271.py`, `v13/code/docs/proofs/continuation-20261025/context-warm-authority-run271/*`, and optionally a new Run271 CI workflow. No edits to PR270-owned `memory.py` or any model/Runtime/canon/gate files.

## RED hypothesis
`ContextOS.warm` reads `memories` and `sources` directly, bypassing `Memory._verified_rows`. A remembered correction with removed/tampered F5 HumanDecision or feedback can be reactivated as a warm item in SHADOW or ACTIVE ContextOS even though ordinary recall rejects it. That would allow a revoked authority source to enter C3's ACTIVE_VIEW through an alternate path.

## Fixed controls
- Actual Runtime+SQLite with synthetic text and an explicitly observed warm memory; verify valid record-only memory reactivates in SHADOW and ACTIVE, including restart.
- Remove HumanDecision; mutate source kind; delete feedback; duplicate decision. All invalid warm candidates must disappear.
- A valid second warm candidate must still fill the two-slot warm budget after invalid candidates are excluded.
- No modification of persisted warm state, no model inference, no native/Redmi claims, no promotion of Age 0 or latent authority.
- Run RED before code, focused ContextOS/Memory/Runtime integration and official privacy scan; preserve raw failures, exits, hashes. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0 and V13 INCOMPLETE remain.

## Expected implementation
Reuse the canonical F1/F5 read-only memory validator, batch candidates before the final two-item warm cap. Do not invent an alternate authority rule or change Memory itself. Stop on unexpected test regression and preserve its raw output.
