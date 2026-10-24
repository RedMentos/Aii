# Run74 closed actual Linux Context OS append provenance evidence

Base Run73 PR106 `f81c8404894f06cebed02f3b4f38af29b9096587`. Canon §8.5 append-only re-entry. Original ContextOS persisted SHADOW hypothetical `planned` transcript and reused it in ACTIVE as though sent to native runner. It also re-entered on same event ID with changed prior user text, or historical transcript missing an `applied` field.

Real full-checkout GitHub Linux CI RED run **40129795646**, job **120978874771**: **76 tests, 3 FAIL**, precisely shadow-to-active, changed source, and missing applied proof. Raw log preserved.

Fix: transcript stores `applied`; ACTIVE re-entry requires previous `applied is True` and exact terminal prior user text, stable prefix and event ID. SHADOW->SHADOW retains hypothetical counterfactual append for research; ACTIVE->ACTIVE valid exact append remains functional. No false native KV reuse claim.

Real full-checkout GitHub Linux CI GREEN run **40129841683**, job **120979013206**: **76/76 PASS**, compileall PASS; official public privacy scan `privacy scan f81c84048..HEAD: CLEAN`. Raw RED/GREEN logs committed byte-for-byte. Existing Context OS suite and Run68-74 tests included.

Evidence tier: real public Linux software/SQLite, not native receiver KV reuse, semantic utility, target Redmi or full V13 acceptance. Gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE.
