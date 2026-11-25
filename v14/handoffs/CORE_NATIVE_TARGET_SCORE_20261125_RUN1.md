# Core & Harness — native target-score handoff

**Date:** 2026-11-25  
**Branch:** `core/v14-native-target-score-20261125-run1`  
**Pre-handoff branch HEAD:** `7c455098c9b4efea955691755490168a7211d76f`  
**Code commit:** `1eee88b1de898d2c9c2dec4670b8ff1d8ec7d8d7`  
**PR:** [#2515](https://github.com/RedMentos/Aii/pull/2515), DRAFT / NOT_RELEASED  
**Parent:** Core [#2512](https://github.com/RedMentos/Aii/pull/2512), head `10c2f66f8c110516e02d165e2b60183199527116`; Perception evaluator source copied unchanged from #2511 latest branch.

## Implemented

1. `native_latent_receiver.cpp` adds bounded teacher-forced scoring of 1–512 target token IDs from the same positive receiver embedding context. Stable log-sum-exp rejects invalid logits; target tokens are decoded only as needed to score subsequent targets.
2. `native_latent_receiver.py` sends token IDs after the float32 payload on stdin, verifies target hash/count, model and binary SHA-256, pinned llama.cpp revision/version, finite per-token log-probabilities, decode status and input-consumed evidence. Android labels require device receipt/build metadata. Injected binaries are SYNTHETIC_FIXTURE only.
3. `native_receiver_utility.py` is carried byte-for-byte from Perception #2511. `native_receiver_task_score.py` provides a 160-receipt, in-memory-only cohort buffer, duplicate rejection, eight-condition completeness checks and evaluator invocation. No target text, token IDs, vectors or receipts are persisted.
4. `native_tokenwise_receiver_probe.py` can attach a source/session-bound LATENT_CANDIDATE receipt. It does not yet produce the other seven conditions.

## Tests and evidence

- LOCAL_LINUX C++17: isolated log-sum-exp/token-logprob helper compiled with `-Wall -Wextra -Werror`; equal logits, invalid token index, NaN, +Inf and all-negative-infinity cases PASS.
- LOCAL_LINUX CPython URL validator tests from the separate Android open-url lane: 17/17 PASS; isolated broker reconstruction 30/30 PASS. These are not tests of this PR's full repository.
- Full Aii checkout/pytest: NOT_RUN; no checkout mounted and GitHub DNS failed.
- Full llama.cpp-linked native receiver build and Python target-score tests: awaiting exact-head GitHub CI; not claimed as passed.
- No GGUF was downloaded or loaded. No real native target score measured. No Android/Redmi device connected; REDMI_UNVERIFIED.

## Related Android action PR

- [#2513](https://github.com/RedMentos/Aii/pull/2513), branch `core/v14-android-open-url-api-20261125-run2`, head `e2774a22c2f9d0a4acfee3c00d1024793b952f61`: visible-consent HTTPS ACTION_VIEW capability, TTY-gated operator path and signed DISPATCHED_UNVERIFIED receipt. Stacked on #2481, DRAFT / NOT_RELEASED. No APK installation.

## Remaining acceptance

The utility evaluator requires all eight conditions for each task:
`NO_MESSAGE`, `EXACT_MESSAGE`, `LATENT_CANDIDATE`, `ZERO`, `SHUFFLE`, `REPEAT`, `OOD`, `ENTITY_SUBSTITUTION`.
It requires at least 20 held-out task groups, at least two sessions and two task families. Candidate must beat every control. The current producer supplies LATENT_CANDIDATE only; cohort remains COLLECTING. Even a complete likelihood cohort is a proxy, not semantic correctness or proof of generated-answer correctness.

No model swap, weight update, B3 activation, production route, phone permission, update request or user-data mutation was performed.

## Next exact executable task

Build a bounded eight-condition matrix producer from source/session-bound control records, reusing the native target-score producer. Run at least 20 held-out task groups across two sessions and two task families against a pinned real GGUF on LOCAL_LINUX; preserve exact input/target/model/binary hashes and per-condition receipts. Require candidate to beat every control. Only after that, arrange a separate explicitly authorized Termux/Redmi measurement with a genuine device execution receipt. Keep B3 OFF until then.
