# Run592 prospective registration — JEF/C2 human feedback binds a committed turn once (2026-10-26)

Owner: GPT automation11. Independent JEF bridge review branch based on verified Run591 PR587 checkpoint `2b48b202d116151fb106a32269069c91b90ff7f0`. File ownership: `v13/code/v13/jefbridge.py`, new Run592 tests/workflow/proofs. No changes to Canon, native cohorts, model/seed/source hashes, Age rights or other owners' branches.

**Read-only defect:** `JEFBridge.outcome(event_id, utility)` trains the symbolic offer utility weights on every call using mutable `turns` rows without checking a matching `JEFBridgeTurn` packet or source refs. A repeated rating replays SGD updates, and a forged/missing packet can still be rated. This is a real C2/JEF learning integrity weakness independent of native JEPA availability.

**Prospective correction:** Validate finite numeric utility and recognized source, real event/generation, a matching latest `JEFBridgeTurn` packet with event/generation/packet ID and readable provenance, and exact selected offer ID/role correspondence between persisted turn rows and packet offers. Reject orphan/altered packet before any SGD or neuromod signal. Record `human_rated` on the turn inside the same CAS as selected-offer updates; a second call returns zero. Delayed feedback to still-retained earlier turns remains allowed; evicted turns stay unlearnable. Preserve existing internal `learn_turn` heuristic, SHADOW/ACTIVE behavior and Age gates. No new native or tool authority.

**Prospective tests:** Real Runtime/SQLite JEFBridgeTurn positive, repeat and restart once-only, missing/tampered packet refuse, mismatched generation/source fail closed, NaN/Inf/invalid source refuse, older retained turn can still receive delayed feedback. Run existing `test_jefbridge`, JEF lifecycle, cache lineage and human precedence regressions with exact-head CI, compile/privacy/SHA-closed raw. Preserve any RED.

**Claim limits:** software-only symbolic JEF; not native C2 training, Body-JEPA or AGI. STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, Redmi UNMEASURED, full V13 INCOMPLETE. Independent review before integration.
