# Run74 prereg — Context OS append-only actual-prompt provenance

2026-10-24. Base Run73 PR106 f81c8404894f06cebed02f3b4f38af29b9096587. Owner only `context_os.py` append-only transcript read/store, new `tests/test_context_append_provenance_run74.py`, CI selection line, Run74 evidence. No changes to pinned budget logic, native, age, approval, model weights or blueprint.

Hypothesis: SHADOW plans are hypothetical and not sent to the runner. Current ContextOS nevertheless stores the planned transcript and re-enters it after operator switches to ACTIVE, falsely assuming a native KV prefix that never existed. It also accepts same event ID with changed prior user source text. Test full-checkout RED: SHADOW->ACTIVE must rebuild; changed prior user content must rebuild; historical transcript without applied flag must rebuild. Controls: SHADOW->SHADOW hypothetical append still allowed, ACTIVE->ACTIVE exact-source append still allowed, unrelated event rebuilds.

Fix: persist transcript `applied` provenance; ACTIVE append requires prev.applied is True, SHADOW retains counterfactual append; require exact last user message text matching transcript terminal user message. No substring source authority or invented KV claim.

Evidence via bounded public Linux CI and official privacy scan; original STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE.
