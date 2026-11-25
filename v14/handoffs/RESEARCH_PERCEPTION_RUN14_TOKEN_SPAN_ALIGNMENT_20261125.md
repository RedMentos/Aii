# Research & Perception — Run 14 handoff (2026-11-25)

## Run evidence

- Start observed: 2026-11-25 13:57:27 Europe/Berlin.
- Completion timestamp: UNKNOWN.
- Repository: RedMentos/Aii.
- Base: PR #2496 head `ace68f1fa44989101849a2c78087aaa03010b5d8` (itself stacked on #2489).
- Working branch: `research-perception/v14-token-span-alignment-20261125-run14`.
- Latest code/document checkpoint before PR creation: `e99f116a17e272d53c29a17faecdbcc3c0de0172`.
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
- `.github/workflows/v14-latent-token-alignment.yml`
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
