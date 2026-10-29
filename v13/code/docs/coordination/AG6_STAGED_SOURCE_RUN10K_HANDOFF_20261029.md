# V13 AG6 staged-source revocation — branch-scoped BUILD_STATE delta and handoff

**Date:** 2026-10-29. **Owner:** Codex/GPT independent review child PR #1125, `codex/v13-ag6-staged-source-recheck-20261029-auto10k`. **Parent:** PR #1124 at `edcbb279dc1503ee0c7f7f556a0d24714eef4972`. No merge, no production integration. Canon, AGENTS, ROADMAP and user decisions remain binding; this delta does not overwrite `v13/code/BUILD_STATE.json`.

## Source and checkpoints

- Prereg `f9b26094e9170df34e6145a65b0929a0c3cc14fb`, before original tests.
- Original fixture attempt `40919812020`, exact head `d7ba42b94616a2d84e72b3029e60350663d45aaa`: 3 ERROR from test fixture using stage summary as persisted batch; **not** evidence of the hypothesized defect. Artifact SHA256 `7cfa61439db4caeff64a24b56365effaee39ffc442dff8af33b638e06d68b9c6`; preserved, not erased.
- Corrected original RED `40920002306`, head `efbea2e82af21eddc8e92b35d9e80c1799ff23da`: **2 genuine assertion FAIL, 1 PASS**, original trainer reached after source revocation; privacy/diff exit0. Artifact `12918260654` SHA256 `b2e531162da4ed742c5e6eeaca338f38a404ddfb81de97b97cc35a199d88d158`; ZIP CRC and 8/8 internal hashes checked.
- Candidate source commit `38a0096028a9262d8a620885acf87e2fc37c32cc`, `v13/code/v13/agi/weights.py` blob `ba563b276352ff3c993d119ea790673c385d6be6`. Validates each staged direct SourceRef with Store.read_source before trainer.fit, records `SOURCE_INVALID` and refuses batch dedup after invalidation.
- Focused software Actions `40920166693`, head `7a09f5a46278711b893b1cd38f4ab6936e88ebbd`: **38/38 PASS** (new 3 plus inherited AG6 controls), compile/privacy/diff exit0. Artifact `12917417787` ZIP SHA256 `537f16c90c4023fc63df3feb6a687c4e7374bd247fdcb7f9af93dd29b2e6d7f6`, CRC and 10/10 internal hashes checked.
- Full software run `40920238606`, workflow-only head `cdb6db4aa0d6e4fa16bb650395bb44e05eb2982c`: **PENDING** as of this handoff. Do not claim full-suite GREEN.
- All three raw ZIPs stored privately in Library `/V13-Checkpoints/2026-10-29/GPT6-Auto10-AG6-Stage-Revocation/`; each was re-materialized and `cmp` byte-exact against original download. No private raw transcripts published.

## BUILD_STATE and claim limit

New narrow software claim: `AG6_STAGED_DIRECT_SOURCE_REVOKED_PRE_FIT_VETO_SOFTWARE_PASS` on the candidate head, **not** weight-learning utility, native training, Redmi proof, or complete revocation safety. This check is immediately before fit, but not a transaction held throughout long model training; a concurrent post-check revocation is still an open race. Rated-answer dependency revocation after staging, user rating mutability, and source kind changes require separate evidence. Existing full-suite frozen run34/run37 source identity tests may remain RED by design when source changes; preserve exact output.

Negative gates remain: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, AG6 unapproved, Redmi unmeasured, V13 incomplete.

## Exact next commands and owner

1. Fetch Actions run `40920238606`, download its original artifact, verify ZIP SHA256, CRC, every internal SHA256SUMS, source HEAD, focused/full/compile/privacy/diff exits and **all** full-suite failure names.
2. Update this handoff and PR #1125 with exact raw outcomes; if only the two inherited frozen source checks fail, keep FULL RED. If any new failure occurs, repair in child branch and rerun without rewriting failed artifacts.
3. Independent reviewer: compare `weights.py` against PR #1124 parent, check that revoked source never reaches fake fit and valid source still does, confirm no activation/age rights changed.
4. Separate next substantive path: training-time rated-answer dependencies and concurrent revocation; no automatic merge.
5. For the fast reproducible software check: `cd v13/code && PYTHONPATH=.:tests:scripts python3 -m unittest -v tests.test_ag6_staged_source_revocation_20261029 tests.test_ag6_rated_answer_dependencies_20261029 tests.test_ag6_rated_source_admission_20261029 tests.test_weight_approval_atomic tests.test_agi_trainers`.

Remaining platform budget: UNKNOWN. No Redmi access in this run.


## Correction after first full-suite RED (2026-10-29, preserve evidence)

The first full run `40920238606` was **not** only the two inherited pinned-source errors: 3213 tests, **1 FAIL + 4 ERROR + 11 skips**, including three new regressions. New: SDFT and neuromod synthetic tests used deliberately unbound fake SourceRefs, which the new fail-closed gate correctly rejected; data-mix poisoning was classified SOURCE_INVALID before DATA_MIX_FAIL. ZIP artifact `12917623119`, SHA256 `10d5bb71f6d7dab85518d52a41ccbb24dbc68095c10cc1341b30eb39f5cc0dbf`, CRC/19 inner hashes verified and private Library re-materialized byte-exact.

Corrective code commit `87fd08ffe7677938be269facd65f06d3ad3a0653` restores DATA_MIX_FAIL precedence **before** source validation; source refusal still occurs before fit. SDFT fixture commit `8a67f4bb47a40d072f795397c50cd4c2759d9f43` now uses a real Store correction SourceRef; neuromod fixture commit `173c6498b7e82b6a9e82e5fbd9719b33af2f992c` uses a real Store human source. These are software-test fixture corrections, not source/model/seed cohort changes. Fast recheck `40921307265` verified both repaired fixtures and source tests but had an **environment ERROR**: `test_learning_invariants` requires numpy, absent from stock Python. Original log preserved; no fake PASS. Pinned numpy venv added at `05e88a984018a5e319b6578b2d4029d9020beac3`, recheck pending. Full pinned rerun `40921336476` at `e3f6e052fca2e79a0f5045843ff0c4455c220ad4` pending.

Do not claim a full-suite pass. Next exact checks: inspect `40921542715` (numpy-focused), `40921336476` (full), verify ZIP/CRC/internal SHA256SUMS and all errors, then update PR #1125. Original frozen run34/run37 RED must remain visible. Child PR #1126 contains identical fixture bytes plus separate approval source guard; verify mergeability before integration.
