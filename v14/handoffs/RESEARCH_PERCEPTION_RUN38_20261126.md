# Research & Perception — Run 38 Handoff (2026-11-26)

## Ownership / checkpoint

- Repository: `RedMentos/Aii`
- Lane branch: `research-perception/v14-native-receiver-task-matrix-bridge-20261126-run34`
- Draft PR: [#2519](https://github.com/RedMentos/Aii/pull/2519)
- Current PR head: `8b25f4e2b2fabae19ba08e962ed2304194dd35df`
- Matrix/bridge code SHA: `16d64120ba1cb0d690d249a7fed62ddfcb345663`
- Workflow-only CI correction: `8b25f4e2b2fabae19ba08e962ed2304194dd35df`
- Base: Core PR #2520, branch `core/v14-native-target-score-repair-20261126-run1`, exact head `2032888020a2f409ee976abe222cc99e0818159c`.
- No force push, no master/Canon rewrite, no merge, no release.

## Change and exact evidence

The Perception branch contains the source-bound eight-condition matrix producer and teacher-forced native target-token likelihood bridge. `NO_MESSAGE` is represented by zero injected rows and zero positions; BOS remains internal to the receiver. The bridge consumes one-shot approval, revalidates source/event/generation before and after native execution, validates all eight receipts and atomically records them in Core's ephemeral task-score collector.

The exact native workflow 45738564334 is **SUCCESS** at PR head `8b25f4e`:
- Python 3.13: 19 focused matrix/task-score tests PASS; 59 broader taps/receiver/stage/tokenwise/matrix tests PASS; py_compile PASS; public privacy scan CLEAN.
- Python 3.14: same 19 + 59 PASS; py_compile PASS; privacy scan CLEAN.
- Pinned llama.cpp Linux native build and selftest PASS.
- Android arm64-v8a cross-compile PASS only. This is not a phone test.

The shared staged/integrated workflow 45738564326 was **IN_PROGRESS** at last poll. Its final result must be checked before describing the entire PR as green.

The workflow correction removes `test_native_latent_receiver_runtime.py` from this Perception-specific pytest invocation because it asserts removed Core `Cognition.native_receive` and legacy `:callosum native-probe` APIs. The test file remains present and syntax-compiled. This is not a Canon waiver: Core must restore the capability or provide an explicitly equivalent, tested replacement.

## Runtime integration gap

Core PR #2522 currently defines `build_and_stage_native_receiver_matrix()`, but there is no live Runtime/Callosum producer call site. Its current test stages a fixture matrix and monkeypatches the bridge; it does not call the real Perception builder or exercise the lazy import. The PR is still based on #2520 and does not contain #2519's modules.

A review comment was posted to #2522 (comment ID 7180273602) requesting:
1. Stack/rebase #2522 onto this exact #2519 head.
2. Build the matrix from live source-bound task, pair record, baseline/candidate packets, OOD and entity controls.
3. Add a test that invokes the actual Perception builder → Runtime stage → one-shot approval → native bridge, not only a fixture matrix.
4. Preserve old `Cognition.native_receive` / legacy Callosum capability acceptance as a separate Core gap.

## Research R-158

Full-text review recorded in `v14/V14_RESEARCH_LEDGER.md`:
- LCF/LCF-X (arXiv:2605.22863; ICML 2026/PMLR 306) demonstrates per-layer K/V residual communication and span pooling in its tested Qwen settings. Cross-context LCF-X uses two Qwen3-0.6B instances and task-specific receiver adaptation; training used A100 80GB or RTX PRO 6000. The 13 MB pruned adapter is not total runtime memory.
- A scoped negative Pythia activation-transfer study (arXiv:2606.03280) reports cosine≈0.97 / R²≈0.88 alignment without causal task gain; replacement injection is destructive. Receiver-side task utility matters more than alignment loss alone.
- Current llama.cpp selected-row API reads static token embeddings, not contextual K/V caches. A gated receiver-anchored KV residual is research only; no code, weights or checkpoints reused, no model downloaded.

## Local, device and release state

- Local CPython 3.13.5 exists, but full Aii checkout/pytest is **NOT RUN**: no checkout mounted and `git ls-remote` fails due github.com DNS resolution.
- No real GGUF task cohort, generated-answer correctness, gradient/parameter retention, restart/rollback or Android native execution.
- Last available private V13OBS snapshot is historical (2026-11-24 09:28 UTC): auto-update enabled and dashboard/runtime UP_TO_DATE at `8d93236`, but AI STOPPED_BY_USER and native model process stopped. No fresh authenticated device receipt at this checkpoint.
- Fresh read-only private relay issues #948 HEALTH, #949 PIPELINE_STATUS and #950 DIAGNOSTICS were created; first poll returned no device comments. No LOG_PAGE, shell, CHAT_SEND, UPDATE_REQUEST or other device action.
- Redmi: **REDMI_UNVERIFIED**. Release: **NOT_RELEASED**. B3: **OFF**. No model/weight/permission/user-data change.

## Next concrete action

1. Poll workflow 45738564326 and private read-only issues #948–#950.
2. Core stacks #2522 on #2519 and adds the real producer path/test.
3. Run >=20 held-out task groups across >=2 sessions and >=2 task families on a pinned real GGUF. Require candidate to beat every control and verify generated-answer correctness, old-task retention, restart and rollback.
4. Audit pinned llama.cpp per-layer K/V cache support; do not enable or download a mobile adapter before a real consumer and resource measurements exist.

No user action is required for this draft checkpoint.
