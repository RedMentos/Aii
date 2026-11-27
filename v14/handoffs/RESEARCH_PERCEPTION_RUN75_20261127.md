# Research & Perception — Run 75 handoff

**Date:** 2026-11-27  
**Branch:** research-perception/v14-a3-ood-calibration-20261127-run72  
**PR:** https://github.com/RedMentos/Aii/pull/2566  
**Code/test HEAD:** 697283e8e0ff5ef95fc4ca19fabab73ab665f9ac  
**Parent/base:** b3896e3a3ba5a85de8ea67f45d123ef8e74da075 (Perception PR #2565 ancestry)  
**Release:** NOT_RELEASED  
**Device:** REDMI_UNVERIFIED

## What changed

1. Fixed the self-generated-message row-budget regression test. The control geometry is the complete latent candidate geometry: BOS baseline plus sender rows. The assertion now compares SELF_GENERATED_MESSAGE.input_rows and position_ids with the LATENT_CANDIDATE condition instead of a stale hard-coded row count.
2. Added a native first-next-token, full-vocabulary Jensen–Shannon audit in v13/code/v13/native/latent_receiver/native_latent_receiver.cpp.
   - PL: LATENT_CANDIDATE vs NO_MESSAGE.
   - CIC: LATENT_CANDIDATE vs same-session/same-task-family DERANGED_MESSAGE other-example donor.
   - Reports JSD in nats and normalized by ln(2); includes input/logit SHA-256 bindings and vocabulary size.
   - Raw logits are not exported or persisted.
3. The native binary advertises the audit capability. native_latent_receiver.py requires that capability, validates schema, model/input hashes, vocabulary bounds, finite JSD bounds and normalized-value consistency, and returns the sanitized audit.
4. native_receiver_task_matrix_bridge.py rechecks the audit against the receiver model and exact approved condition inputs and returns it with the per-task diagnostic.
5. Preserved input_rows and context_rows in each sanitized native condition receipt. This fixes the direct-text reference consumer's missing row-geometry field.
6. Added C++ self-tests for identical distributions, positive divergence, symmetry, the ln(2) upper bound, NaN and all-negative-infinity rejection; Python tests cover audit binding and cross-matrix negative controls.

## Exact evidence

- Local Linux scratch: C++17 JSD helper compiled with g++ -std=c++17 -O2 -Wall -Wextra -Werror and passed identity/symmetry/bounds/NaN/all-negative-infinity checks. Python scratch JSD invariants also PASS. These are isolated algorithm checks, not a full repository build.
- Full local Aii checkout/pytest/native build: BLOCKED; no checkout mounted and git ls-remote failed because github.com DNS was unavailable.
- Predecessor exact workflow 46074686027 on 2d302094b80715166bf428f05efde200fe6c9d85: pinned Linux API build PASS; Android arm64-v8a cross-compile PASS; focused source-bound matrix/task-score tests PASS. Python 3.13/3.14 full runtime jobs failed at the missing input_rows receipt field (fixed in current HEAD) and a separate Core-owned audio-composer source pin.
- Current exact-head native workflow 46075616512 for 697283e8e0ff5ef95fc4ca19fabab73ab665f9ac: QUEUED at handoff time. Do not claim its C++ build, Android cross-compile or Python tests passed until it completes.
- Shared staged/integrated workflow 46075014940 failed before the Perception receiver path: 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests. Blockers are stale Core/QA pins for scripts/integrated_audio_context_candidate_20261121.py and v13/cognition.py, unsupported lifecycle source vision.py, and two migration assertions returning PARTIAL instead of UPDATED.
- The bridge/audit is diagnostic only. No real GGUF inference, no normal-turn Runtime consumer, no trained cross-model adapter, no generated-answer correctness, no B3 activation and no Redmi test were performed.

## Research interpretation

R-194 (Zhang & Emu, arXiv:2607.26773v1, 2026-07-29; preprint, not peer-reviewed; full text reviewed in the earlier entry) motivates the causal comparisons. This implementation adapts PL/CIC as first-next-token distribution sensitivity. JSD does not prove that the receiver understood the message or improved the task. The same-family deranged control is a donor-identity comparison; CAG/SSG still require paired task correctness, not target-token likelihood alone. No new paper is claimed as newly read in this run.

The native API remains pinned to llama.cpp revision b29c606e28a01b1bc8c1351026a0fa6e616bf6c4; no external code, model weights or new dependency was added. The upstream project is MIT-licensed; this patch is original code using the existing pinned API.

## Next executable step

1. Close exact-head CI on 697283e8e0ff5ef95fc4ca19fabab73ab665f9ac; repair any failures in this lane.
2. Persist the validated PL/CIC audit in candidate task-score receipts and aggregate it across source/session-disjoint held-out groups with paired bootstrap confidence intervals.
3. Add actual task-accuracy CAG and SSG, plus equivalence controls; do not treat logprob or JSD as correctness.
4. Only then run at least 20 source-disjoint groups across at least two sessions and two task families on an already-authorized pinned real GGUF. No model download/swap or permission change without separate explicit approval.
5. Keep B3 OFF until actual receiver consumption and task-utility evidence exist. Coordinate Core/QA pin repairs separately; Perception does not own those files.
