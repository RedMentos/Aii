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


## Run 13 follow-up — 2026-11-23 11:37 UTC

### Exact code and review state
- Release-development base readback: `gpt6/v13-private-remote-bridge-20261111` at `dfa3945b2bbfdb65d932db74e02f402435494e84`.
- PR #2436 code/test follow-up commit: `c611e45178da854125e11a9b852b4c015cf8046f`. Later commits on this branch update only the handoff/PR evidence; use PR #2436 metadata for the current branch HEAD (still DRAFT / OPEN / NOT_RELEASED).
- The source-forget guard intentionally scans **all pre-dispatch C4 FocalCycle packets**, plus available FocalItem and ActionSelection provenance, for the same event/generation. Earlier C4 cycles may have influenced the eventual action even if their items are absent from the final coalition. This is deliberately conservative and may cause extra rollback/replay until the producer persists complete per-cycle item lineage.
- Added `test_memory_forget_conservatively_invalidates_nonfinal_focal_cycle_source_after_replay_row_eviction`: the earlier-cycle-only source is absent from the final-cycle T8 receipt, but forgetting it still invalidates the checkpoint after its replay row is evicted. The fixture now supports multiple ordered C4 cycles.

### Verification — exact environment boundaries
- Exact previous code head `0d290072d6f6e4d59267d369cad8457f7848df23`: GitHub Actions run 45164462030 passed optimizer-resume/source-forget on Python 3.13 and 3.14; run 45164462029 passed staged-runtime and integrated-regression. These PASS results apply to `0d29007`, **not** the new `c611e45` follow-up.
- New head `c611e45`: no exact-head JEPA or staged/integrated run is visible yet. The only newly visible run 45166837128 is the safe-additive workflow and is SKIPPED by policy; it is not a test pass.
- LOCAL_LINUX isolated SQLite 3.46.1 query reproduction: PASS for (a) same-event earlier C4 cycle source is conservatively selected, (b) other-event source is excluded, (c) post-action packet is excluded, and (d) PREDICTION-stage packet is excluded. This validates only the SQL predicate, not the repository integration.
- LOCAL_LINUX full Aii checkout/pytest: BLOCKED / NOT_RUN; no checkout is mounted and GitHub DNS is unavailable. No repository test is claimed locally.
- Redmi/Termux: REDMI_UNVERIFIED. No phone, private relay, CHAT_SEND, UPDATE_REQUEST, LOG_PAGE, shell, model/weight swap, permission change or device mutation was used.

### User-visible effect and remaining connections
- If integrated, C4 coalition refs become part of source-verified T8 receipts and the forget guard can invalidate checkpoints even when the bounded replay row has been evicted. This is a Memory deletion/rollback correctness improvement, not a user-facing chat improvement by itself.
- The verifier still recovers only the final C4 coalition for the T8 receipt. This is not the complete pre-action C3 context (history, executive, ContextPlan and other admitted prompt sources), not trained native latent transfer, not GGUF/body-weight learning, and not Android learning.
- Core still needs a complete source-bound pre-dispatch context receipt for the actual C3 prompt. JEPA can then validate/merge it and carry it through source-disjoint learning, B1/B2 receiver readout, replay and source-forget. Existing #2405/#2426 receiver/temporal work remains a separate stacked, unintegrated path; do not duplicate it blindly.

### Research notes for the shared ledger
- **iSDFT**, arXiv:2609.24646 (2026-09-28): full paper reviewed. It chooses the closest student distribution that meets a per-token teacher-information budget, with the local tilt solved by bisection, and adds a separate frozen-base KL anchor. Reported 73% of retention evaluations within 0.5 points of base vs 52% for the strongest baseline; the paper also reports that the anchor's main effect is retention, while information budgeting primarily controls acquisition. Official repo: https://github.com/KickItLikeShika/iSDFT. No root LICENSE file was found/read back, so no code was reused. The implementation requires Python 3.12, CUDA BF16, colocated vLLM, and keeps student + EMA teacher + frozen base models resident; requirements pin Torch 2.9, Transformers 4.57.1, vLLM 0.12 and TRL 0.24. It is not a Redmi implementation. Candidate V14 experiment only: apply an information budget to a small trainable reader/control distribution with an explicit old-policy anchor, then compare against full-teacher, fixed interpolation, and no-anchor controls. Do not replace WorldJEPA's grounded outcome objective with token distillation.
- **STONE**, arXiv:2611.18916 (2026-11-13): abstract-level primary-source review only. It moves agreement from hard tasks to easier model-generated stepping-stone problems, then conditions a teacher on the worked stones while withholding their final answers from the student. The abstract reports results on five math benchmarks for Qwen3-4B/8B; no public implementation repository or code license was verified. Possible Dream/Replay experiment: generate source-anchored easier subproblems as non-authoritative candidates, require independent agreement and later observed/human outcome before any target use. Never promote synthetic stones to facts or tool authority.
- No model, code, dataset or weights were downloaded or imported; no model/license swap is proposed.

### Next executable step
1. Obtain Boss review of #2436 and exact-head CI for `c611e45`; do not merge or mark C4→T8 complete without it.
2. Coordinate with Core on the full pre-action C3 context receipt (history/executive/ContextPlan/observer/Enlightened sources), preserving producer ownership.
3. After the current-base source chain is reviewed, connect verified T8 lineage to the existing B1/B2 temporal/episodic receiver path with source/session-disjoint holdouts, delayed-outcome negatives, retention, restart and rollback.
4. Keep retrieval and body readouts SHADOW; optimizer promotion and native model-weight changes remain OFF.

**User action:** none required.


## Run 14 superseding correction — 2026-11-23

This section supersedes the Run 13 note that described all-cycle forgetting as conservative over-invalidation while the T8 receipt contained only the final cycle. Boss review correctly identified that mismatch between causal holdout provenance and deletion rollback.

- The new candidate unions the bounded source refs from every pre-action C4 FocalCycle for the same event/generation into the immutable T8 receipt. Source-disjoint train/holdout partitioning and source-forget now use the same recorded trajectory influence set.
- The final cycle is validated against its FocalItem union. The real producer persists FocalItems only for the final active coalition; earlier cycles have only their FocalCycle provenance. An earlier cycle at the 16-ref producer cap is therefore ambiguous and rejected, rather than silently omitting possible sources.
- The cycle sequence must be contiguous (1..N), the per-cycle cap is 16, and the total unique source-ref union is bounded at 64. Prediction-stage and post-action FocalCycle packets are excluded.
- New regressions: (1) source A in cycle 1 and source B in cycle 2 both enter the T8 row; (2) a 16-ref earlier cycle without per-item receipts is rejected; (3) after replay-row eviction, forgetting a post-action-only FocalCycle source leaves the checkpoint active; (4) forgetting the earlier-cycle source invalidates the checkpoint.
- Test fixtures now mirror production: only the final cycle persists FocalItem packets; earlier cycles persist only FocalCycle provenance.

Code commits on candidate branch:
- authority union: 435565bcd3231837c05d197327c33d990992daa6
- source-forget scope alignment: e72c5b46c0557e772883a893934da6beb2fd5c73
- multi-cycle / post-action tests: 25de9601f7a93c5ffa4952a7f5558b93a5742072

Verification: full repository compile/pytest is BLOCKED / NOT_RUN because no Aii checkout is mounted locally and GitHub DNS is unavailable. The isolated SQLite source-forget predicate check from Run 13 is not a substitute for these new repository tests. Exact-head Python 3.13/3.14 JEPA, staged/integrated, migration and privacy checks must run on the replacement PR before review. No local numeric weight update, no GGUF mutation, no Android deployment, and no Redmi-native test is claimed.

This candidate is based on the Run 13 C4→T8 branch but is intended to replace the earlier one-cycle-only candidate after exact-head CI. The earlier #2436 PR remains open until the replacement PR is created and reviewed; no merge/force-push has occurred.


## Run 14 follow-up — strict packet-order cutoff for C4/T8 provenance (2026-11-23)

### Additional defect found by code review
- Store timestamps are generated with `time.time()`; the T8 verifier and source-forget guard previously relied on `packet.created <= action.created` to distinguish pre-action C4 packets.
- A post-action FocalCycle/FocalItem written in the same clock tick can share the exact float timestamp and be misclassified as pre-action. The previous regression only covered a strictly later timestamp.
- Runtime ordering is deterministic: FocalLoop persists all FocalCycle/FocalItem packets, then C5 persists its committed ActionSelection, and only afterward does Store.start_action create the action. The causal boundary is therefore the committed ActionSelection's rowid in the shared `packets` table.

### Implemented on this branch
- T8 authority now captures the unique committed ActionSelection rowid and accepts only FocalCycle rows before that packet boundary; cycle ordering also follows packet rowid.
- WorldJEPA source-forget scans ActionSelection/FocalCycle/FocalItem only through the same committed ActionSelection rowid. The learning receipt and deletion rollback therefore share one causal cutoff.
- The replay-row-eviction regression now inserts a valid cycle-3 FocalCycle plus FocalItems after the action, rewrites their timestamps to equal the action timestamp, verifies they are excluded from the T8 row, then forgets that source and requires the checkpoint to remain active.

### Verification boundary at commit preparation
- LOCAL_LINUX full repository checkout/pytest: BLOCKED / NOT_RUN; Python 3.13.5 is available, but `git ls-remote https://github.com/RedMentos/Aii.git` fails because github.com DNS is unavailable.
- No Redmi/Termux receipt, model download, weight mutation, permission change, or deployment was performed. REDMI_UNVERIFIED.
- Exact-head GitHub workflows are required to validate the new regression and source-composition pins before review. This remains a source-provenance/rollback integrity fix, not native JEPA latent transfer or GGUF weight learning.
