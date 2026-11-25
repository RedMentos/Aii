# Research & Perception — Run 14 handoff (2026-11-25)

## Run evidence

- Start observed: 2026-11-25 13:57:27 Europe/Berlin.
- Completion timestamp: UNKNOWN.
- Repository: RedMentos/Aii.
- Base: PR #2496 head `ace68f1fa44989101849a2c78087aaa03010b5d8` (itself stacked on #2489).
- Working branch: `research-perception/v14-token-span-alignment-20261125-run14b`.
- Latest code/document checkpoint on the rebased branch: `a4ea0704af84f9567f6c0b7a750848198e794f74`.
- No force-push, merge, release, deployment, model download or device action.

## Functional change

Problem found in the existing tokenwise adapter path: it checked contiguous token positions and row counts, but those checks do not establish that sender row *i* and receiver row *i* describe the same source span. Different tokenizers can split the same source differently. A receiver input builder could therefore accept a position-only alignment that has no token-boundary evidence.

Changed:
- `v13/code/v13/latent_adapter.py`
  - Added tokenwise adapter schema v3 while retaining event-pooled schema v2 compatibility.
  - Added `align_token_rows_by_char_span()`: maps sender rows to receiver token spans by overlap-weighted aggregation.
  - Requires sorted non-overlapping spans, at least 0.80 coverage for each receiver span, exact source SHA-256, per-sequence alignment ID, and sender/receiver tokenizer revisions.
  - Tokenwise fit now rejects position-only rows, duplicate/gapped positions, overlapping receiver spans, inconsistent source hashes/alignment IDs, train/holdout source-hash leakage, and a mismatched receiver tokenizer revision.
  - Native input builder checks the exact receiver tokenizer revision.
  - Event-pooled schema-v2 fit and projection are unchanged.
- `v13/code/tests/test_latent_adapter.py`
  - Added different-segmentation alignment, coverage failure, span-overlap failure, missing-proof rejection, source-hash leakage, tokenwise adapter fit, tokenizer mismatch, and checkpoint metadata round-trip tests.
- `.github/workflows/v14-latent-token-alignment.yml` (shared with parent branch #2496 so it is present in the PR base)
  - Added focused Python 3.13/3.14 compile + adapter/tap/audit tests + public-repo privacy scan.

The alignment helper is a geometric prerequisite only. It does not establish semantic transfer, gradient learning, task utility, native execution or production readiness. Current persisted tap records still lack per-token character offsets; `fit_from_tap_records()` therefore remains event-pooled schema v2. The new v3 path is not yet fed by a real paired tap cohort.

## Research

Full paper review recorded as R-143 in `v14/V14_RESEARCH_LEDGER.md`:
- Deng, Liu & Zhu, *Augment the Cache, Replace the Activation: A 2x2 Study of Internal-State Sharing*, arXiv:2610.22026v1, 2026-10-15.
- The paper's positive activation replacement result depends on oracle layer/position alignment and one Qwen family; its GPT-Neo→Qwen cross-family tests collapse to controls.
- It uses receiver-side task accuracy plus no-op, position, mis-source and answer-disjoint controls. The reported results are single-seed and have other stated limits.
- No OSS code or weights were imported; no official code repository was identified. No model weights/dependencies were downloaded.
- V14 consequence: held-out MSE, cosine or a changed next-token distribution are not semantic-use proof. Keep B3 OFF until receiver task utility and negative controls pass.

## Tests and evidence status

- Exact local repository checkout is not mounted in this runtime; full repository pytest has NOT_RUN locally.
- Focused CI is defined but was not yet polled after this checkpoint.
- No native model/GGUF run, gradient/parameter update, retention test, Linux native-token measurement, Termux run or Redmi receipt.
- `REDMI_UNVERIFIED`; `NOT_RELEASED`; GitHub push does not imply deployment.
- Existing sibling PR #2498 contains Run 13's A4/RAW-EAR work on a sibling branch; this PR is stacked on #2496 and must be reconciled with #2498's ledger/next-action append during integration.

## Next concrete action

1. Poll this branch's exact CI and fix any test failures.
2. Have the native tap producer emit verified tokenizer byte/character spans without storing source text; only then can real tokenwise paired fitting be exercised.
3. Add a receiver-side task-utility evaluation using answer-disjoint/source-disjoint holdout, exact-forward parity, no-message, zero, shuffled, mis-source, position and OOD controls; keep event-pooled and tokenwise evidence separate.
4. Coordinate with Core on the native receiver path. No production B3 promotion, weight changes, model swap or Android claim from this work.


## Run 14b — CI repair, event-pool loss measurement and new research (2026-11-25)

### Changes on this branch

- Fixed the tokenwise test fixture to pass the list-shaped vectors required by the adapter contract; NumPy arrays in the fixture were the cause of the first focused-CI failure.
- Corrected the source-hash leakage test so every token row belonging to the selected holdout source receives the same leaked hash and matching alignment binding. The previous fixture changed only one row and therefore correctly failed earlier at the within-source consistency guard instead of reaching the train/holdout leakage assertion.
- Added _event_pool_discarded_energy_ratio() to the read-only latent_alignment_audit.py. For nonzero-position rows, it computes residual energy around the event mean divided by total activation energy. Cohort output reports median/p95 for sender and receiver. The field explicitly states that this is descriptive within-event variance, not semantic information loss or task utility.
- Added tests for constant vs varying token rows and assertions that the persisted paired-tap audit reports the metric. The existing audit remains read-only and does not load models, export raw vectors, train adapters or change weights.
- Added research-ledger entry R-144 after full review of Chen et al., arXiv:2606.13594v2 (v2 2026-10-05). See ledger for method, benchmark limits, CC BY 4.0 paper license, absent verified code release and model/data-license caveats.

### Exact evidence

- Local Python isolated formula reproduction: PASS. Constant nonzero-position rows produced 0.0 residual ratio; two orthogonal rows produced 0.5; the existing toy-tap pattern produced 0.1. This is not the full repository pytest suite.
- GitHub focused workflow V14 latent token-span alignment, run #12, on code/test SHA 10b07cedd60db0b61dcbd7fdc493ceb6f6c48d84: PASS.
- GitHub V13 runtime deployment integrity, run #2517, same code/test SHA: PASS.
- GitHub V13 staged context and integrated regression, run #5060, was still IN_PROGRESS at the last poll; do not count as PASS until its final conclusion is read.
- The branch head advanced after these code/test checks for the R-144 ledger append; the current branch HEAD and exact CI readback must be rechecked before merge.
- Full repository local pytest was NOT_RUN: no repository checkout is mounted in this execution environment and the direct Git remote probe returned no checkout. The isolated Python check does not replace CI or repository-local tests.
- No native GGUF model was loaded here; no native generated tokens, task accuracy, gradients, persistent parameter diff or retention/restart test. No Termux or Redmi run. REDMI_UNVERIFIED.
- PR #2501 remains a draft stacked on #2496; NOT_RELEASED. GitHub push/CI is not a device deployment.

### Cross-lane integration finding

Core PR #2499 head df19e207b96df8d942f0499e29ffa7d21d6fcb9a has a failing exact workflow: V14 native latent receiver staged runtime, run #907 / run ID 45623391201. Its Python suite reports 82 passed / 1 failed. The failure is test_callosum_probe_runs_synchronously_only_from_idle_operator_and_uses_last_source: after the test's arm-probe call returns ARMED, the following native-probe reaches consume() with no PENDING record. Review comment #7164056126 was posted on PR #2499 with the stack and a request to trace the state/lease interaction without weakening local-TTY, one-shot, source/model-binding or exclusive-lease checks. Other CI on that Core SHA includes runtime deployment integrity #2512 and staged context regression #5055 as PASS; this does not cancel the dedicated receiver workflow failure.

### Research consequence

R-144 is not a drop-in Android design. Its positive results use 4B/8B/14B Qwen3 KV caches (plus a 7B cross-family case), dense per-layer/per-KV-group transforms, 30k reconstruction steps and 2k generation steps. The estimated cache payload is 27.2–30.2 MB/example and its FLOP estimates omit cache processing/transport. The present V14 LATENT_PREFIX_V1 path carries one event-mean vector with no source text, so it is context-unaware and much more compressed than the paper's method. Keep it diagnostic-only.

### Next concrete actions

1. Recheck current branch HEAD and all CI after the ledger/handoff append; fix any new failure before asking for review.
2. Coordinate with Core on the #2499 PENDING-approval/lease failure; rerun its exact dedicated workflow after repair.
3. Extend the real native tap producer to emit tokenizer byte/character spans without storing source text. Current persisted tap packets do not yet provide those offsets, so tokenwise fitting is not yet fed by real paired tap data.
4. Build the next receiver-utility experiment on source-disjoint task data: compare event-mean vector, multiple span vectors and tokenwise receiver-compatible state under both context-aware and context-unaware settings, with exact-forward parity, no-message, zero, shuffled, row-shuffled, mis-source, position and OOD controls. Keep B3 OFF until task utility, not just input/logit effect, is shown.


## Cross-lane correction — Core PR #2499 (2026-11-25)

The earlier comment on PR #2499 incorrectly described the failing test as arming and then losing a PENDING approval. Exact commit comparison showed that the test at df19e207 did not call arm-probe at all; the earlier read used a later branch snapshot. A correction was posted in PR comment #7164132935. Core commit 8502afe adds the missing explicit arm-probe step and corrects the preflight-unload call ordering. The dedicated V14 native latent receiver staged-runtime workflow #911 on 8502afe is PASS. The previous approval-state diagnosis is withdrawn. This is still staged Python/C++ control-path evidence, not a real GGUF semantic/task-utility test or Redmi proof.

## Current branch CI poll

At the latest poll, PR #2501 current head 64eb3cf693f97f3f44999912858d651a1b682a01 has focused V14 latent token-span alignment workflow #14 PASS and V13 runtime deployment integrity workflow #2519 PASS. V13 staged context and integrated regression workflow #5062 remained IN_PROGRESS; it must be polled again before the handoff is treated as fully green.
