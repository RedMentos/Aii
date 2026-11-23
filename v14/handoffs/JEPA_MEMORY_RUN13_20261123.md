# JEPA & Memory — Run 13 handoff (2026-11-23)

## Verified starting point

- Development/release branch before this change: gpt6/v13-private-remote-bridge-20261111
- Exact base SHA: b20e9b1f3dd53af472055adb43da628785494ec4
- Release push CI at that SHA: 37/37 observed check-runs SUCCESS (21 workflow runs); this is GitHub CI, not a local or Redmi measurement.
- Issue #1904 latest sanitized private receipt (#767, 2026-11-23 10:55:05 UTC): installed SHA still 8bf44cb50e855a6dba0c91f64f60d8daddcbdc9c, auto-update enabled, Runtime/Dashboard CI_WAIT, last_error NONE. The receipt predates this run's new branch and does not confirm its installation.
- Latest stored turn remains 57.739 s total / 41.627 s TTFT / 38.945 s prefill / 751 prompt tokens / 2 generated tokens; correctness UNKNOWN. B1/B2 probes remain TIME_BUDGET at 53.2/54.2 s with zero valid offers in the latest five-turn aggregate. No new CHAT_SEND, UPDATE_REQUEST, LOG_PAGE, shell, model/weight swap, permission change or device mutation was performed.

## Implemented code change

The existing JEPA T8 verifier consumed ActionSelection.provenance, but the current runtime can still emit an event-only ActionSelection. The final C4 FocalCycle already records the selected coalition, and the matching FocalItem packets carry each member's source refs.

This change makes the JEPA verifier:

1. Read the final pre-action FocalCycle for the same event and generation.
2. Resolve each coalition ID to exactly one pre-action FocalItem.
3. Validate every FocalItem SourceRef against the live Store source/blob/span.
4. Compare the FocalCycle.provenance set with the full union of its FocalItem refs. A producer-side truncation, missing member, duplicate member, conflicting digest, over-bound scan or revoked source is rejected.
5. Merge verified coalition refs with the existing ActionSelection refs before the immutable T8 receipt is issued. The existing multi-source holdout partition and source-forget invalidation then receive those refs without a separate data path.

Files:
- v13/code/v13/world_jepa_store_authority.py
- v13/code/tests/test_v14_world_jepa_runtime_port.py

This is a JEPA consumer-side recovery of the already-persisted C4 coalition lineage. It does not claim full C3 prompt lineage: history, executive state, ContextPlan and other prompt-only sources still need a pre-action, source-bound producer/receipt. It does not implement native latent injection or GGUF weight updates.

## Tests added/changed

- Positive: final FocalCycle + FocalItem refs are merged into the verified T8 receipt and persisted learner row.
- Negative: a 17-source coalition whose FocalCycle provenance is truncated to the current producer's first 16 refs is rejected.
- Negative: a revoked/deleted FocalItem source is rejected.
- Retention/unlearning: the existing active-checkpoint/replay-row source-forget regression now sources its extra context ref through FocalCycle rather than only ActionSelection.

Local execution:
- Full local checkout and Python test environment were not available in this run; exact local tests are BLOCKED / NOT_RUN. GitHub Actions on the exact PR head must provide the next executable evidence.
- No local Linux-native model training, Redmi-native training, or phone test is claimed.
- Redmi status: REDMI_UNVERIFIED for this change.

## Research note

- JEPA-TTT, arXiv:2610.00722 (submitted 2026-09-30; NeurIPS 2026 Workshop on World Models in Physical AI): adapts an action-conditioned JEPA dynamics predictor from observed transitions, with dense temporal replay and predictor/optimizer/replay persistence. The paper reports an 83% mean reduction in five-step latent prediction MSE and a 153% mean best-planning-score improvement over its frozen-JEPA baseline across eight fixed dynamics shifts. Its matched persistence control keeps update count fixed and compares retaining versus resetting predictor/optimizer state. Limitation: each deployment tests one fixed shift; sequential shifts, return-to-old dynamics and catastrophic forgetting are not evaluated. V14 can reuse the persistent optimizer + dense replay + matched-reset ablation idea, but must not adopt frozen encoder/reward head as a permanent architecture rule. Primary sources: https://arxiv.org/abs/2610.00722 and https://jepa-ttt.github.io/. The project page exposes no source-code repository or code license; no code was reused.
- Geometry of Forgetting: Representation Flux in Continual Learning, arXiv:2608.15854 (2026-08-16): reports that large sample-level representation displacement can precede forgetting and proposes FlowLess-R, a replay-sample representation anchor. V14 follow-up experiment: log per-replay-sample latent drift before/after each update and compare replay-only, replay+reference-anchor, and no-replay controls while preserving nonzero new-task learning. Treat this as a candidate metric/regularizer, not as proof that representations should be frozen. No reusable code/license was verified. Primary source: https://arxiv.org/abs/2608.15854.

## Remaining gaps and next action

- The C4 coalition source set is now recoverable by the JEPA verifier, but it is not the complete C3 context set. Core should persist a source-bound pre-dispatch Context/ActionContext receipt covering history, memory, executive and ContextPlan sources; JEPA can then merge and validate it.
- The B1/B2 temporal prompt receiver remains a separate draft integration (#2405 / #2426 dependency chain); do not claim it is delivered to Redmi. Its exact source-pin/QA integration is still unresolved.
- Next executable JEPA step: connect the verified C4/C3 source lineage to the B1/B2 receiver, then run source-disjoint holdout, replay-on/off, rollback/restart and negative-source-forget tests on the exact release-base stack.
- Auto-updater: enabled, but the latest authenticated receipt still shows the phone at the older installed SHA with CI_WAIT. No manual Termux command or new UPDATE_REQUEST is warranted; wait for a later authenticated PIPELINE_STATUS after exact push CI.
- User action: none required for this source-only PR. No model download/swap or learning permission change is proposed.
