# JEPA & Memory — Run 7 (2026-11-23)

## Status

- Work branch: \`jepa-memory/v14-temporal-episodic-recall-20261123-run7\`
- Parent integration branch: \`qa/v14-jepa-source-lifecycle-rebase-20261123-run16\`
- Parent PR: [#2402](https://github.com/RedMentos/Aii/pull/2402), whose verified head at branch creation was \`de4143790bc9ff7e3dc32c40fbc2a4fe9d09dd64\`
- This is a stacked JEPA/Memory change. It does not merge or deploy the parent branch.
- New feature status: implemented in this branch; exact CI result pending.
- Local execution: BLOCKED. The current container has no Aii checkout; \`git ls-remote https://github.com/RedMentos/Aii.git HEAD\` failed with DNS resolution error. Python is present, but this is not a local compile/test of repository sources.
- Redmi: \`REDMI_UNVERIFIED\`; no authorized live device receipt was obtained in this run.
- Release/deployment: \`NOT_RELEASED\`. No updater request, model swap, data migration, or device action was performed.

## Implemented slice

The existing temporal JEPA learner already persisted verified T8 experience rows, trained an encoder/predictor with EMA, retained disjoint holdouts, and exposed gated numeric B1/B2 readouts. Its learned latent was not yet being used as an episodic memory retriever by the body consumers.

This branch adds a read-only episodic recall path:

1. \`TemporalWorldJEPAStoreConsumer.episodic_recall()\` reconstructs the current 2/3-transition query from the same session history used by the B1/B2 receiver.
2. It verifies the query history against current T8/ActionOutcome/CorollaryCopy/SourceRef records.
3. It rebuilds candidate windows and admits **only** \`active.train_window_ids\`; holdout windows are excluded. Candidate windows sharing query action IDs or source digests are excluded.
4. It samples at most 256 training windows deterministically across the temporal span, embeds them with the already-trained temporal JEPA encoder, and ranks by latent distance. The encoder loaded for the receiver matrix is reused ephemerally, avoiding a second checkpoint load.
5. Before returning an episode, every transition in that candidate window is reverified and its complete SourceRef is read back. Only observed terminal outcomes are recalled; censored/unknown outcomes are not presented as completed results.
6. The prompt receives at most the two closest compact rows: action, latent distance, observed duration, success flag, output-character count, and an 8-character source-digest prefix. No prior raw source text is exposed.
7. The full window action IDs, source digests and SourceRefs are kept in the BodyState audit, which is itself source-backed and present in QueryPacket provenance.
8. Recall is nonblocking, bounded by a 50 ms foreground budget, read-only, and has no action authority or weight-update authority. Prompt-budget trimming drops this optional episodic context before dropping the primary temporal receiver context.

This is a **learned-latent nearest-episode SHADOW readout**, not a completed Future-Aware Recall retriever, not a native cross-organ latent bridge, and not evidence of GGUF/base-weight updates.

## Changed paths

- \`v13/code/v13/world_jepa_temporal.py\`
  - Added train-split-only, source-verified \`episodic_recall()\`.
  - Added deterministic temporally stratified candidate cap, query/candidate source-disjointness, per-window provenance revalidation, read-only audit and time budget.
  - Reuses the current receiver's ephemeral model instance when the checkpoint SHA matches.
- \`v13/code/v13/bodyview.py\`
  - Adds compact episodic recall to the existing B1/B2 temporal body context.
  - Stores full provenance in the BodyState audit; no source text is copied into the prompt.
  - Preserves the 700-character body-state budget and trims optional recall first.
- \`v13/code/tests/test_v14_world_jepa_postcommit_runtime.py\`
  - Adds synthetic Runtime/SQLite B1 and B2 prompt-consumer checks.
  - Verifies train-only selection, query/source disjointness, SourceRef readback, no raw text disclosure, no temporal state-version mutation, and a no-checkpoint negative control.
- \`.github/workflows/v14-temporal-world-jepa.yml\`
  - Adds \`bodyview.py\` and the postcommit integration test to compile and pull-request path filters.

## Test and evidence status

- Parent QA branch #2402: its latest comment at the time of inspection records 20/20 checks green. This is CI evidence for the parent head only, not for this branch.
- This branch: CI pending until the new PR/workflow run completes.
- Local Linux exact-source compile/tests: BLOCKED by missing checkout and DNS failure. Do not relabel CI as local.
- Termux/Redmi runtime, native model inference, native B1/B2 generation, native gradient/weight changes, Android updater and device rollback: NOT TESTED in this run.

## Research note — Future-Aware Recall

Kim et al., “Learning What to Recall: Adaptive Multi-Cue Episodic Memory for World Models,” arXiv:2609.34677 (submitted 2026-09-28), is directly relevant. It trains retrieval using predictive utility from the realized future, then keeps inference future-blind; cue-specific scores are fused by a query-dependent gate. It also shows that recency, geometric overlap and visual similarity can each be misleading when the world changes. The paper explicitly leaves writing, compression, forgetting and higher-order interactions among multiple recalled memories open, and its experiments are controlled simulation rather than Android deployment.

Official implementation: \`sony/far\`, revision/readback for this run; its LICENSE is CC BY-NC 4.0. Its declared stack includes PyTorch 2.7+, torchvision, diffusers and many research dependencies; the README's quickstart reports about 14 GB GPU memory on an H100. No FAR code, checkpoints, datasets or weights were copied into Aii. The non-commercial license and heavyweight diffusion/GPU stack make direct product/Redmi reuse inappropriate without a separate rights and feasibility decision.

V14 adaptation: this branch takes only the architectural direction that episodic recall should be judged by predictive usefulness rather than recency alone. It does **not** yet train a retriever from delayed future utility. The next research/implementation step is a small source-bound cue scorer trained from delayed T8 outcomes, with a future-blind inference contract and disjoint holdout comparison against (a) recency, (b) normalized raw-state distance, (c) current JEPA-latent distance, and (d) shuffled/random retrieval. It must retain source lineage, checkpoint/restart/rollback and report utility/retention before it can move beyond SHADOW.

## Next concrete action

1. Run the exact 3.13/3.14 GitHub workflow for this branch and repair any compile, integration or source-provenance failure.
2. Re-read the newest QA/JEPA heads before rebasing; keep the branch stacked only while #2402 remains the current source-lifecycle integration base.
3. Ask the Boss/Integrator to update \`V14_WORK_BOARD.json\`, \`V14_LIVE_WORKPLAN.md\`, \`V14_CANON_COVERAGE_INDEX.md\` and \`V14_USER_NEXT_ACTION.md\` with this branch's verified SHA/PR/CI status. Those shared files remain Boss-owned.
4. After independent review, integrate through the normal release pipeline; a GitHub push is not a Redmi deployment.

**User action:** keine Aktion nötig. No model, weight, permission, updater or device setting was changed.
