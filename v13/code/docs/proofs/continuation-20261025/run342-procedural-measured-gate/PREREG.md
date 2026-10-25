# Run342 preregistration — FastForward procedural authority (2026-10-25)

Base: `2fbab509094658a3ef88ed3f83dbfe3cf0268c41` (Run341 / PR337 chain). Owner: this isolated review branch. File ownership: `v13/code/v13/fastforward.py`, dedicated Run342 tests/workflow and narrow assertions in `test_fastforward_reflex.py` / `test_fastforward_latency_gate_run300.py`. Do not edit frozen SourceHandoff sources, Canon, source/model/cohort hashes, Runtime, learning/age approvals, or active native jobs.

## Observed RED / canonical contradiction

`FastForward.record_turn` may mark a pattern `READY` from SHADOW agreement plus **predicted** latency only. Its own persisted gate explicitly records `canonical_gate_pass: false` and `latency_evidence: PREDICTOR_ESTIMATE_NOT_MEASURED`. Yet `FastForward.procedural` currently sets `apply=true` in `ACTIVE` mode, allowing the unmeasured habit to skip B1/B2 passes. The original Run300 and procedural tests explicitly expect this unsafe transition. Canon §85.6/G-PROCEDURALIZATION-004 requires measured latency and energy decrease, accuracy noninferiority, reopen-on-error, and preserved source/rule constraints **before** replacing deliberation. An explicit human ACTIVE switch is necessary but not sufficient proof of utility.

## Proposed minimum correction

Retain all predictor, observation, shadow, persisted READY, explicit ACTIVE, calm/salience and reopen logic. Gate `apply` on verified canonical eligibility as well as human ACTIVE and calm. Existing predicted-only READY remains a SHADOW proposal even after ACTIVE; expose a clear denial reason. No fabricated measured proof or new auto-promotion. A future separately preregistered, hash-bound measured-utility verifier is needed before an actual automatic shortcut can be enabled. If the current schema has no trustworthy measured verifier, **fail closed**, including against a manually toggled single Boolean.

## Tests / evidence / limits

Before fix: new adversarial test should show predicted-only READY+ACTIVE applies incorrectly. After fix: predicted-only READY+ACTIVE stays in deliberation; forged boolean without measured evidence also stays blocked; missing gate stays blocked; salience bypass remains; SHADOW remains; restart persistence retains denial. Update two historical positive assertions to match the corrected authority contract, retaining original observation/READY checks. Execute source-only real Runtime/SQLite tests, original FastForward outcome-once/CAS/sleep tests and privacy scan on exact GitHub head; keep RED output if a test fails. No native performance, energy, learning, Redmi or G-PROCEDURALIZATION-004 PASS claim. STEP2/B3/Body-JEPA/AG6/Redmi/V13 negative gates unchanged.

Exact next: add RED-first test; run exact-head source-only workflow; then smallest implementation and GREEN CI; independently inspect diff and remote bytes.