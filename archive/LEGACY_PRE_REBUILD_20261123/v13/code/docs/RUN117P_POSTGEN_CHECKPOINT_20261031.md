# Run117P — B1/B2 → typed JEF → C3 post-generation integrity (review-only)

## Provenance and immutable baseline

Owner: hourly GPT-6 continuation, separate review branch `assistant/v13-run117-role-postgen-shadow-20261031-hourly11`, parent `5cc9852fbadec73bfc0f7f4fdbb7f52340be3d14` (Run116 independent original-native auditor, PR #1495), stacked on Run116 #1494 and Run115K-R #1493. This branch is **not** merged into production. Canon `V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`, AGENTS, user decisions, model pins and frozen cohorts remain unchanged. No runtime, model or frozen test fixture modified.

Original Run116 native Actions 41224639354 at source `df08a4ce311317bdfd322ba7c7520d9fe8fb2b93`: original artifact 13051756857 SHA256 `71de9bb7bc2899f5aee67f58b55d13514d0a9b0d870cd98ae5e8f2f1850d11c5`; ZIP CRC PASS, 27/27 inner SHA256SUMS PASS, source 2199/2199 files independently audited in Run116 auditor; original audit Actions and raw in private `/V13-Checkpoints/2026-10-31/Run116-Native-Pilot/`. Native actual calls: B1/B2 18 FINAL/reaped; C3 18 FINAL/reaped, no native JEF/C2. Frozen six paired tasks: RAW_TWO_SOURCE_ROLE **1/6**, TYPED_JEF_ROLE **6/6**, TYPED_JEF_WITH_BODY_ROLE **6/6**. Five tasks improved from raw to typed; adding B1/B2 to typed changed **zero** task outcomes. Typed JEF payload contains the correct deterministic choice and remaining budget *before C3*, and C3 is explicitly instructed to copy it. Thus this is a narrow source/formatter noninterference signal, **not** evidence of C3 reasoning gain, Body complementarity, learned utility, generalization, or STEP2 acceptance.

## New executable candidate

`v13/code/v13/jef_b1b2_c3_role_postgen_shadow_candidate.py`: default OFF and requires both operator/callback opt-in. Consumes the actual Run115K-R real SQLite/Context OS B1/B2 + typed JEF → C3 USER-role bridge; calls a **trusted** callback once with a defensive copy of the frozen prompt. Before callback: verifies exact typed candidate, two original USER sources, persisted ContextPlan lineage, B1/B2 offers, JEF zero authority and SHADOW mode. After callback: rechecks Store epoch, source, offers, JEF, plan, generation, mode and prompt; accepts only bounded unique-key JSON `choice` and `remaining` exactly equal to the pre-bound typed JEF candidate. Rejects wrong choice, wrong remaining, duplicate/extra keys, boolean/nonfinite values, stale corrections, tampered SQLite/blob, callback prompt mutation and errors. Even PASS returns only digest and byte count, never raw response, output or permission token. `output_committed=false`, `tool_dispatches=0`, `learning_authority=delivery_authority=0`, `jepa_weight=0` and all negative gates remain.

**Scope limits:** this guard is not a sandbox, cannot undo generator side effects outside Store, cannot detect every external no-op/rollback, and does not itself invoke native C3 or prove semantic truth. It deliberately creates a SHADOW ContextPlan during preflight. The callback must be trusted and controlled. It is not connected to production output or tools. The source's preexisting fixed JEF grammar is narrow; this does not solve open-ended language understanding.

## Evidence

On the extracted, exact original Run116 phone source (software/Linux, no native model call in this package), Python 3.13 focused new + inherited real Store suites: **57/57 PASS** in 5.609s; `compileall` PASS. Original local focused raw SHA256 `529e89dc669b6a10cac3c1627ec0411f5662ae55cdeb4e909b1bd6c13bd1b7a0`. New 13 tests include real SQLite and deliberately wrong synthetic body hypotheses, external SQLite mutation, source blob corruption, late correction, mutated plan/offer, duplicate JSON and output mismatch. The first external no-op SQLite update counterexample was not observable through `PRAGMA data_version`; the test was corrected to a content-changing external update and the detection limitation explicitly recorded above. No false claim that every external write is detected. Remote Git blobs must be checked against the local Git blob SHA and CI original raw artifact before review acceptance.

Local source SHA256 `44d37af1518cd38931bf875555b349b8eb70be782c19f989affbee0494c2568c` / Git blob `7a873d99694a566f672989a339d3f1c0c642b693`; local test SHA256 `2a734bd189ff699a144df79623baf406334cfd82cf4fe0d9a4164c2500f0a706` / Git blob `919001e356a692628ffb7f88a9b2c526dcc4ab6c`. Both Git blobs independently fetched and verified on this review branch. Local evidence and source are backed up in private Library folder `/V13-Checkpoints/2026-10-31/Run117-Postgen/`; public GitHub contains no private data.

## Open, next and gates

- Next: run independent GitHub Actions software CI at exact branch HEAD with original ZIP artifact, source/fixture hash verification, privacy scan and raw hash closure. Download and independently inspect raw artifact before claiming CI success.
- Next after CI: add a read-only causal-attribution report that flags deterministic answer injection and lack of body contribution; a **new disjoint preregistered** cohort is required for any generalization or utility claim. Do not rescore frozen seed1019 as a new test.
- Native C3 postgen execution, actual Redmi, JEF/C2 native, STEP2, B3, Body-JEPA, World-JEPA learning and whole V13 acceptance remain open. All existing REDs remain RED. Do not enable output, tools or learning from this candidate.

Reproduce (with extracted current-chain phone source and this branch's two files installed):

```sh
cd v13/code
PYTHONPATH=. python -m unittest -v tests.test_run117_b1b2_jef_c3_role_postgen tests.test_run115k_realstore_bridge_review tests.test_run115k_postassembly_authority_review tests.test_run116_b1b2_jef_c3_native tests.test_jef_two_source_role_formatter_candidate tests.test_two_source_pointer_shadow_candidate tests.test_b1b2_c3_source_envelope_candidate
python -m compileall -q v13/jef_b1b2_c3_role_postgen_shadow_candidate.py tests/test_run117_b1b2_jef_c3_role_postgen.py
```
