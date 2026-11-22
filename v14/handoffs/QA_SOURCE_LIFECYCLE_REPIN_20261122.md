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
