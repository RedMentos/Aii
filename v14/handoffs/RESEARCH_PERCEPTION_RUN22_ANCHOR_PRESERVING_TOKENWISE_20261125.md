# Research & Perception Run 22 — Anchor-preserving tokenwise latent input

Date: 2026-11-25
Owner: Research & Perception
Branch: research-perception/v14-anchor-preserving-tokenwise-20261125-run22
PR: https://github.com/RedMentos/Aii/pull/2511
Base: Perception PR #2508, parent SHA e333b5c3da2448ef6d188f2278672f7f692ac76e
Code/test SHA: 87c8c7ecdf18ac42ad2753568991a2c4e32078ae

## Change

1. native_tokenwise_pairing.py now reconstructs the native receiver input-embedding manifest digest, validates the extractor receipt, enforces the exact UTF-8 byte-span partition, and checks every aligned receiver row hash/span against the manifest's ordered rows. The session-disjoint fitter therefore rejects a pair record whose receiver vector is detached from the native extractor row manifest, even if pair IDs and the outer record digest are recomputed.
2. Added build_anchor_preserving_native_receiver_input(). It keeps the exact receiver input-embedding rows as the base and adds only a per-token residual toward the projected sender row. The residual is norm-capped and gain-limited (default gain 0.10; maximum 0.5). It returns the existing native receiver's zero-based contiguous prefill geometry and source/model/adapter digests. The existing replacement-style builder is unchanged.
3. No raw text is returned or persisted. No native inference, training, gradient, model-weight update, production route or authority promotion is performed.

## Research

- XBridge, Yang et al., arXiv:2608.11676 (2026-08-12), accepted NeurIPS 2026: https://arxiv.org/abs/2608.11676. It combines receiver-vocabulary lexical anchors with gated latent enrichment; its LEB has 264M trainable parameters and is evaluated on 7B-class models. Official repo code LICENSE is Apache-2.0; checkpoint license not verified; no code/weights reused.
- Cárdenas Piepereit, arXiv:2608.16347v2 (2026-11-09): https://arxiv.org/abs/2608.16347. Above-chance representation retrieval did not predict generation-level causal utility across all pairs; only one of three decoder-only pairs met the pre-registered causal criterion, and generated text often did not answer the source question.
- The new helper is a small residual interpolation experiment, not XBridge LEB, cross-attention, semantic transfer or a universal latent bridge.

## Verification

- LOCAL_LINUX CPython 3.13.5: python3 -m py_compile /tmp/anchor_residual_harness.py PASS; isolated harness 4/4 PASS.
- Full local Aii checkout: NOT_AVAILABLE / NOT_RUN.
- The current PR #2511 branch head is tracked directly on GitHub; code/test SHA remains 87c8c7ecdf18ac42ad2753568991a2c4e32078ae. On the current head, adapter-contract 3.13/3.14, staged-runtime, integrated-regression, offline 3.11/3.14, privacy and bridge-security checks are QUEUED. Earlier head c1e3e20 had offline 3.11/3.14, privacy and bridge-security PASS; its staged/integrated checks were still running when superseded. The v14-latent-token-alignment workflow filter was corrected in e8b8d95229f3c17db099468f4767ccfad18be612.
- Native GGUF receiver inference, task utility, Android arm64/Termux and Redmi: NOT_RUN / UNVERIFIED.

## Integration and next owner

Core PR #2510 is the runtime capture lane. It should rebase/consume this helper after review and call the native receiver only under existing explicit probe approval. Acceptance requires held-out task utility against exact-message, no-message, zero, shuffled, repeat, OOD and entity-substitution controls; old-task retention; restart/rollback; and exact-GGUF PSS/RSS/TTFT. B3 remains OFF.

## Device and user action

Owner-read DIAGNOSTICS returned NO_LIVE_RECEIPT. The last authenticated private snapshot (2026-11-24) reported auto-update enabled and runtime/dashboard UP_TO_DATE at 8d93236, but AI STOPPED_BY_USER; historical only. Current installation remains unverified. REDMI_UNVERIFIED; NOT_RELEASED. No update request, shell command, model/weight/permission/data change or deployment. No user action is required.
