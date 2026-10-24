# V13 Run35 — WP-Z8 source-root lineage guard (SHADOW only)

Exact parent: PR #70 / `c8215449b5a7249679d514d8b5b10370bd818612` (Run34). Original Run31 v2 source/test reproduced **byte-for-byte** (Git blobs `f909435b18904473a802ce321871b68cf23aaf46` and `3048db050e3d08ad72baf60878052e22f0a49e41`). Canon, original preregistered cohorts and production files untouched.

## Defect and bounded improvement

The original Run31 v2 explicitly treats opaque source IDs as unverified. Four claimed sources can all repeat one upstream wrong label and yield `SHIFT_CANDIDATE` without proving independent evidence. This guard takes a *caller-supplied, closed, hash-fingerprinted registry* mapping each source ID to a claimed upstream root and a claimed quality ceiling; de-duplicates same-root votes per case/window, rejects contradictory aliases and unknown sources, and prevents row quality claims from exceeding the registry ceiling. A known four-alias single-root counterexample now becomes `INSUFFICIENT_EVIDENCE` rather than an apparently corroborated shift.

**No trust escalation:** Registry root IDs and quality remain unverified claims; SHA-256 is only integrity fingerprinting, not signature/authentication. Even when all four claimed roots are distinct, the guard returns `UNVERIFIED_SHIFT_SIGNAL`, `registry_authenticated=false`, `source_independence_verified=false`, `canonical_gate_pass=false` and `SHADOW_NO_AGE_ACTION`. No AgeControl rights, learning, model call, or production wiring. This does NOT establish actual source independence or reopen the original G-AGE-REOPEN-001 gate.

## Evidence

`python -m unittest discover -s tests -v`: **21/21 PASS** (14 new adversarial and 7 inherited exact Run31 tests). `python -m compileall -q scripts tests`: PASS. Raw logs and SHA256SUMS in evidence. Original v2 alias counterexample and guarded result in `evidence/run35-adversarial-original-v2.log`. These are **software/synthetic**, no Linux native model, no Redmi, no native LP3, no full repo suite/privacy scanner. The registry cannot authenticate producer identity or semantic independence; a malicious registry can claim fake roots.

## Next

Independently review root/identity assumptions, then integrate only after actual provenance issuance from independently controlled, authenticated producers is specified and validated. Bind source hashes, case/window lineage and calibration outcomes, preregister fresh streams, compare against original Z8 K1–K7. Continue other canonical functional work in parallel; no gate promotions.

Gates unchanged: STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Z6a `FAIL`, Z8 `FAIL`, full V13 `INCOMPLETE`.
