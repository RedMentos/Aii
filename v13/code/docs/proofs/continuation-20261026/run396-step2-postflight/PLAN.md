# Run396 — independent Run394 native postflight and temporal-provenance audit

2026-10-26. **Owner:** scheduled GPT continuation; source-only independent of active Run395 Linux-native owner. Files owned: `v13/code/scripts/run396_step2_pilot_audit.py`, `v13/code/tests/test_run396_step2_pilot_audit.py`, `.github/workflows/run396-step2-audit.yml`, this proof directory. No edits to frozen Run394 source, model catalog, runtime, Z2/Z2b/Z2c or Run395 job.

**Base:** Run395/PR390 exact initial head `48d2119dbbc7077da10b625ca4ff5819bfc74730`, stacked on Run394/PR389, not main. Run395 native job is independent and may be running. This package must not start additional heavy inference.

**Motivation:** Run394's inherited Z2c `b2_wrong_rule_rows` treats an accurately quoted *historical* rule as wrong if the current turn explicitly supersedes it (Delta/Ember/Fable). The old quote is not necessarily a hallucination; the final committed tool decision must use the current revision. Audit raw rows and provenance separately, without altering preregistered scoring.

**Input:** Unmodified Run394 pilot directory with exact manifest, `step2_{O,P,S}_s20.json`, `tool_{O,P,S}_s20.json`, `summary_{O,P,S}_s20.json`, `RUN394_RESULT.json`. Validate all row SHA, consumer message hashes, preregistration hashes, fixture hash, model/runner unchanged claims, source identity, complete 42 rows and no wrong committed tool. Fail closed on absent/extra/duplicate/invalid rows and nonfinite utilities. Report historical B2 rule quotes as `historical_quote`, not hallucination; distinguish current-source override and committed wrong action. Report paired P−O/P−S on each fixture, no significance or causal claims from a two-fixture pilot.

**Tests:** Synthetic valid and adversarial fixture/report corruptions; no model or native inference; CI privacy CLEAN. **No promotion:** STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA/jepa_weight=0, Age0, no Redmi proof, Run389 full suite RED, whole V13 incomplete.

**Next:** Apply to the *actual* Run395 artifact only after native execution completes and raw ZIP is integrity-verified. A synthetic unit test cannot substitute for actual native evidence.
