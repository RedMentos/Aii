# Run67 — JEF lifecycle exact source-ID matching

Base Run66 PR99 `978c41a2ebd15b0696c510d024b50cc0487c478f`. Scope only read-only `jefoutcome.lifecycle` and new exact source lineage matcher, no learning/weight/approval mutation.

**Original RED:** feedback source ID `src1` matched a manifest with `source_ids=["src10"]` because the old lifecycle searched serialized JSON as a substring. This could falsely claim L4 update proposal and L9 promotion even when no update depended on that source.

**Patch:** parse update manifests as JSON mappings and match only exact string IDs in `source_ids`; malformed manifests and malformed source lists fail closed. All L0–L11 stage names, Store state, human feedback and approval gates unchanged. Existing real update evidence still matches when IDs are exact.

**Tests:** 12/12 pure software tests PASS; 12/12 Python -O PASS; 2000/2000 randomized exact-vs-prefix synthetic lineage trials PASS; compileall PASS. Original RED and raw evidence losslessly archived as `RUN67_RAW_EVIDENCE.tar.xz.b64` (decoded SHA256 `547b25762f259dbd0529b8a8c779058b046f420d162d90aa7803efc24fcb7f8d`). Source and test Git blobs verified. Three actual `jefoutcome.lifecycle` SQLite integration tests authored but NOT RUN due unavailable full checkout.

**Limitations:** No complete repository suite, official privacy scan, actual V13 Store, native models or Redmi. This only makes the lifecycle report less likely to overclaim; it does not prove that any learning stage was completed.

**Reproduce:** `cd v13/code && python -m unittest -v tests.test_jef_lifecycle_sources tests.test_jef_lifecycle_integration_run67` (second requires full checkout). Random review script is inside the raw archive.

**Next:** independently execute real SQLite lifecycle integration and full repository tests/privacy scan; verify manifest schema and active component linkage on real Store before any promotion claim. Continue other canonical packages.

Gates unchanged: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; `jepa_weight=0`; full V13 INCOMPLETE.
