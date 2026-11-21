# JEPA & Memory handoff — durable T8 SourceRef lineage and revocation rollback

Date: 2026-11-21
Lane: JEPA / Memory
Parent work: PR #2186 (optimizer/replay ablation branch)
State at authoring: implementation candidate; CI and Redmi proof pending

## Gap addressed

The persistent WorldJEPA learner admitted trusted T8 transitions only after the authority verified the complete SourceRef, but the replay/checkpoint rows retained only source ID and content hash. Span and modality were discarded after admission. That made the long-lived numeric replay state less auditable and prevented the learner from reliably invalidating a checkpoint when one of its source records was later revoked.

## Code change

- Persist the complete SourceRef (source_id, sha256, char_start, char_end, modality) on each admitted experience and pending replay row.
- Bind the experience set to a separate source_ref_sha256 digest without changing the checkpoint's existing source_sha256 contract.
- Upgrade Store state schema v3 -> v4. Legacy rows are rehydrated from the authoritative EventEnvelope and their source blobs are revalidated once during migration.
- On normal reads, verify the lineage digest and source-table metadata in bounded batches. A revoked/missing source invalidates the active checkpoint; restore the previous checkpoint only when its own complete source set is still valid. Otherwise clear the learner state and prune orphan checkpoints.
- Make receiver-matrix and planner readback pass through the same reconciliation path before exposing a stored readout.
- No raw source text is copied into replay state, telemetry, PR descriptions, or this handoff.

## Regression coverage added

- V14 learning test: v3 -> v4 migration preserves the checkpoint hash, a subsequent update creates a second checkpoint, and revoking a source used only by that update rolls the learner back to the first valid checkpoint.
- V13 staged-runtime test: the postcommit worker creates two checkpoints; revoking one second-cohort source makes planner readback stale and restores the first checkpoint.
- Both tests use synthetic SQLite Store events. They are not Redmi or native-GGUF training evidence.

## Environment and evidence

- LOCAL_LINUX: BLOCKED — no repository checkout was present; git ls-remote to GitHub failed during DNS resolution. No local Python compile/test is claimed.
- CI: pending for the new branch head.
- TERMUX/REDMI: REDMI_UNVERIFIED; no live device receipt was available in this run.
- Native GGUF body weights: unchanged and unverified. The learner remains a numeric WorldJEPA checkpoint path; no B1/B2 native weight edit is claimed.
- Deployment: NOT_RELEASED. A GitHub push is not an Android deployment.

## Research notes

- JEPA-TTT (arXiv:2610.00722; NeurIPS 2026 World Models in Physical AI workshop) retains predictor parameters, optimizer state, and dense replay across episodes. Its eight evaluations each use one fixed dynamics shift; the paper explicitly leaves sequences of shifts and forgetting of previously learned dynamics open. This supports persistent optimizer/replay, but motivates an A-to-B-to-A return-to-old-dynamics test before stronger claims.
  - Paper/project: https://arxiv.org/abs/2610.00722 and https://jepa-ttt.github.io/
- ComposeCL (arXiv:2609.06986, submitted 2026-09-07) composes data, function, and weight anchors with merged LoRA across 100 sequential tasks; the reported average final retention is 34.9% versus 1.2% for naive sequential fine-tuning, averaged across three datasets and three seeds. Its official code is MIT-licensed, but the paper-scale reproduction uses Qwen3-4B, bfloat16, and CUDA; it is not a direct Android dependency or a proven V14 implementation.
  - Paper: https://arxiv.org/abs/2609.06986
  - Code/license/runtime: https://github.com/cozheyuanzhangde/compose-cl

## Next executable work

1. Run the exact CI workflows on this commit and repair failures before asking for review.
2. Add a source-disjoint A-to-B-to-A dynamics-return experiment. Record frozen-before-update, after-B, and after-return losses on the same A and B holdouts; compare uniform replay, hard replay, and no-update control.
3. Keep the planner consumer SHADOW-only until Core provides a real B1/B2 consumer contract; numeric role readouts are not native latent coupling or GGUF weight learning.
4. Obtain a consented Redmi receipt before making any Android performance or deployment claim.
