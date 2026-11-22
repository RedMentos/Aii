# QA & Android — Store/source-forget integration and exact staged-runtime pins

Date: 2026-11-22  
Owner: QA & Android  
Candidate branch: `qa/v14-source-lifecycle-repin-final-20261122`  
PR: #2359  
Base: JEPA/Memory #2351 at `ffb81c435ce02bc0a7477e28cfcefecc464baa75`  
Code head before this handoff-only refresh: `ad1832f9938154f5a9ad2767b33f0b43b4bb2474`

## Scope and ownership

This is a combined stacked candidate. It carries Boss #2355's Store generation/rollback serialization and Memory source-forget lifecycle integration, including the three later #2355 follow-up commits:

- `3c410d560e657cf4b5efaaa9e2f66bc09fb0c848` — lifecycle composition against JEPA source-forget and Store promotion locks
- `a73b279179cd00b7eed69ad12fc32d11fde20c63` — memory/world lifecycle pin
- `f9c9c187eb3870fa9bdd3015e9ef89de61f17b02` — Python 3.13/3.14 workflow selectors

The QA portion binds the source lifecycle, archive guard, online-world, C3 resume, memory/world, feedback, context recall, WorldJEPA resume, Termux recovery, integrated stage and runtime deployer to exact current bytes.

**Do not merge #2355 and #2359 independently.** #2359 currently carries the Store/Memory code from #2355. After exact CI, the integrator should either merge #2359 as the consolidated #2351-dependent stack and close #2355 as superseded, or merge #2355 first and retarget/rebase #2359 as a pure QA pin-rebind. #2351 remains a required dependency. No release approval is implied.

## Defects observed

1. The earlier A5 UI-lease/source-lifecycle run rejected the updated Store SHA in the source-lifecycle composer before the staged read/revoke regression could run.
2. The first integrated retry then exposed a second stale pin in `integrated_online_world_candidate_20261110.py`: it still expected the pre-Store-lock `v13/store.py` SHA. This blocked JEPA optimizer-resume, Python 3.14 staged startup, Lab-Age staged consumption and two-checkout migration. The migration harness fast-forwarded both checkouts but correctly reported PARTIAL/ERROR because runtime staging failed.

## Changes now present

- Keep Store's RLock across generation promotion/rollback preflight and final SQLite transaction. Recheck the exact pending update, base generation, path/hash/manifest, parent lineage and declared live source rows before commit.
- Keep Memory source-forget's JEPA-file-lock → Store-RLock ordering through tombstone, dependent artifact cleanup and final refcount/unlink.
- Use the latest #2355 source-lifecycle composer, with its exact Store/Memory pins and the current nested archive-guard SHA.
- Preserve the distinct old Store SHA where downstream guard/stream candidates still need to replace their pre-composition pin.
- Carry the latest Python 3.13/3.14 JEPA/source-forget workflow selector and the QA A5 path filter.
- Rebind the full consumer chain:
  `archive guard/source lifecycle → online-world → C3 resume → memory/world → feedback bootstrap → context recall → WorldJEPA resume → Termux recovery-12 → recovery-21 → integrated stage → runtime deployer`.

No Age permission, tool permission, training mode, model selection or installed-phone setting is changed by the QA pin work.

## Static readback verification

At code head `ad1832f9938154f5a9ad2767b33f0b43b4bb2474`, the fetched GitHub branch bytes verified **14/14 direct SHA-256/Git-blob edges**:

1. archive/source-lifecycle Store SHA
2. source-lifecycle Memory SHA
3. source-lifecycle nested archive-guard SHA
4. online-world Store SHA
5. C3-resume → online-world SHA
6. memory/world → C3-resume SHA
7. memory/world → source-lifecycle SHA
8. feedback → memory/world SHA
9. context recall → feedback SHA
10. WorldJEPA resume → context SHA
11. Termux recovery-12 → WorldJEPA SHA
12. recovery-21 → recovery-12 Git blob SHA
13. integrated stage → recovery-21 SHA
14. runtime deployer → integrated-stage SHA

The readback is a source-integrity check, **not** an execution test.

## Test and release boundary

- **Previous exact-head CI:** on the earlier head `92b26f81...`, JEPA optimizer-resume, staged Python 3.14, Lab-Age and migration failed from the stale online-world Store pin. Those failures are not hidden or counted as passing.
- **Current exact-head CI:** the runs for `ad1832f9938154f5a9ad2767b33f0b43b4bb2474` are queued/pending: JEPA source-forget, staged/integrated, Lab-Age, owner-read Python 3.14, migration, runtime deployment, A5 and private bridge. No current CI PASS is claimed.
- **LOCAL_LINUX:** no Aii checkout is mounted in this execution container; full local pytest/compile is BLOCKED/NOT_RUN.
- **REDMI/ANDROID:** the candidate is not installed or exercised. The release branch remains `c4eb82deec915f65894c20d6ebbaf0ebf58fa335`; PIPELINE_STATUS #582 reports it up to date, while the newer HEALTH #581 reported runtime UNAVAILABLE. Existing read-only `:status` request #583 remains open; no duplicate request or CHAT_SEND was issued. No post-candidate or 20-turn device acceptance is claimed. REDMI_UNVERIFIED.

A previous private diagnostics snapshot still shows slow C3 prefill and B1/B2 TIME_BUDGET/zero valid offers. That remains the whole-system P0 acceptance gap; this source-composition repair does not claim to fix response quality, native latent exchange or live learning.

## Next executable QA step

1. Wait for all exact-head workflows to finish.
2. If the source-forget or staged jobs fail, inspect the first exact pin/traceback and fix the upstream consumer chain once; do not relax release gates.
3. If green, ask Boss/Integrator to choose the #2355/#2359 consolidation route and rerun the exact release-base matrix.
4. Only after a CI-green release commit may the existing authorized private owner-read path request an update; then obtain a separate PIPELINE_STATUS receipt. Do not claim Redmi PASS without a real device receipt and live 20-turn acceptance.

No user action is required at this stage.


## Run 14 — nested archive Store-pin correction — 2026-11-22 19:15 CET

**Code-bearing parent:** `1d17dc0bb04cae3cd749bd4801254733a232bfb4` (QA branch). This is a candidate source-composition repair, not a release.

### Exact current-head failure and correction

- The first A5 run after the Memory/C3/observer rebind (run `45055010763`, Python 3.13 and 3.14) reached `source_lifecycle_lock_integration_candidate.py` and failed at the nested archive-guard Store pin. The source Store SHA was `bc7ab8edfd26bf0222ebcccbf57c95612f3fe305646eb46571b35b6f72942bd1`, but the frozen archive-reader and archive-stream candidates still carried their own old Store pin `40a387e24f8c4d9533bde484c1c82c1dd700517fa652469b4eea7b8b21a471bb`. The composer incorrectly tried to replace the *source Store* pin inside those downstream candidates.
- Added the distinct `OLD_ARCHIVE_STORE_SHA` for that legacy downstream pin and used it for both archive-reader and archive-stream rebinding. The source Store SHA remains independently checked in `PINS['store.py']`; the generated Store SHA is what the disposable composed candidates now bind to.
- The prior failure was exact and reproducible on both Python versions: `test_staged_store_read_open_is_linearized_with_revocation` failed with `ambiguous lifecycle candidate anchor: guard store pin`, while the other A5 tests passed (17 passed, 5 subtests, 1 failed per version).
- Added a focused regression to `test_v14_store_source_blob_serialization.py` that builds the disposable candidate and asserts both archive guard and archive stream contain exactly the generated Store SHA and no longer contain the stale legacy pin.

### Rebound consumer chain

- Memory cleanup anchor: current `Memory._forget_source` uses 16-space nesting under the Store RLock; the source-lifecycle overlay now replaces that exact block and keeps `cleanup_unreferenced()` inside the same lock ordering.
- C3 resume → Body/World: `integrated_body_world_candidate_20261110.py` SHA-256 `70adca144879efdb9f6c8803ea43b0041ce81b33431c5e8dc3eb209237c3c525`.
- Current Store source: `bc7ab8edfd26bf0222ebcccbf57c95612f3fe305646eb46571b35b6f72942bd1`.
- Observer fairness Store pin rebound to that exact Store source; archive guard/stream downstream pins rebound to the generated Store output.
- Consumer chain was recomputed bottom-up through Memory/World, feedback, ContextOS, WorldJEPA resume, Termux recovery-12, recovery-21 Git blob, stage and runtime deployer. Current code-bearing deployer SHA-256 at parent `1d17dc0` is `fe8bae1b05196e2bb785bde7ad5b1b4bd9adc8ae1bd398b7c6d2fb0e139c4573`.

### Proof boundary

- The new exact-head CI has **not yet run** on this test/hand-off follow-up. The previous A5 failure is not counted as a pass.
- LOCAL_LINUX full Aii checkout remains unavailable; no local full-suite run is claimed.
- Private owner receipts: #581 HEALTH reported `runtime=UNAVAILABLE`; #582 PIPELINE_STATUS reported runtime/dashboard `UP_TO_DATE` on installed `c4eb82deec915f65894c20d6ebbaf0ebf58fa335`; existing read-only `:status` request #583 remains open. No duplicate request, CHAT_SEND, UPDATE_REQUEST, LOG_PAGE or remote shell was issued.
- No Redmi installation, Android native test, model/weight change, permission change or user-data mutation. REDMI_UNVERIFIED; PR #2359 remains DRAFT and stacked on #2351/#2355.

**Next:** exact A5 3.13/3.14, staged/integrated, JEPA optimizer-resume/source-forget, Lab-Age, migration and deploy workflows must complete on the new exact head. Fix the first real failure without relaxing gates. No user action is needed.
