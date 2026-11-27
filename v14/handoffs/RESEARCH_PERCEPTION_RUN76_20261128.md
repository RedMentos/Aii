# Research & Perception — Run 76 handoff

**Date:** 2026-11-28  
**Branch:** research-perception/v14-a3-ood-calibration-20261127-run72  
**PR:** https://github.com/RedMentos/Aii/pull/2566  
**Code/test SHA:** 6d3cf4a874462be3cbf250d1b566ff1c7cabde48  
**Base:** Perception #2565 / `b3896e3a3ba5a85de8ea67f45d123ef8e74da075`  
**Release:** NOT_RELEASED  
**Redmi:** REDMI_UNVERIFIED  
**Run start/end:** UNKNOWN / UNKNOWN

## Change

Fixed the four focused Python failures in #2566's synthetic task-score fixture. `RECEIVER_SHA` was not defined; the PL/CIC audit now binds the receiver hash to the already-pinned fixture manifest value `RECEIVER["model_sha256"]`. The change is test-only; no production code, model, weight, permission, data or runtime authority changed.

The branch's current diagnostic implementation already has:
- the 13th `SELF_GENERATED_MESSAGE` receiver-matrix condition;
- native first-next-token full-vocabulary JSD for PL and CIC;
- paired exact-match task-accuracy summaries for CAG and SSG;
- source-disjoint group/session/family balance and bootstrap confidence/equivalence summaries.

The 20-group path is only a synthetic fixture. The cohort collector is explicitly ephemeral and the evaluator returns `persisted=false`; no durable cohort evidence, raw logits, prompts, token IDs or hidden vectors are stored.

## Exact test evidence

- LOCAL_LINUX scratch, CPython 3.13.5: a minimal fixture/hash/bounds check PASS. Not the full repository suite.
- Parent exact native workflow 46081870981 at `6a4df8c9ecabdaafab81f691248449c32da6ecbb`: py_compile PASS; pinned llama.cpp Linux build PASS; Android arm64-v8a cross-compile PASS; Python 3.13 and 3.14 each had four failures from the undefined fixture symbol. Fixed at `6d3cf4a874462be3cbf250d1b566ff1c7cabde48`; new exact-head CI has not yet been observed.
- Shared staged/integrated workflow 46081871090: FAIL, 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests. Failures are outside this PR's changed files: Core audio-composer source pin, Core lifecycle source support for `vision.py`, Core cognition observer pin and QA migration assertions expecting UPDATED where the tested updater reports PARTIAL.
- Full local Aii checkout, pytest and full native build: BLOCKED / NOT_RUN because no checkout was mounted and GitHub DNS was unavailable.

## Cross-lane NPY preflight

Exact source readback shows #2576's current `vision_ui_frame_ingress.py` blob `14198bbd33b5394c787fe31b9fbce7778cbd11e0` lacks the NPY header preflight while its test blob `6a1b7df21d2d2a4985725c6f2d9cb16538d6f7e3` contains the allocation-bomb test. Current Perception #2563 code blob `6572cd4a3516824b1b5f7618c6fdf7a090f74807` includes the preflight; exact paired tests passed 31/31 on Python 3.13 and 31/31 on 3.14. Current #2565/#2570 OOD-aware code blob `8f2b6d36cf4852ecc16da6ef0ef1639a0ead3332` and test blob `31c6fab9124967e9cb49c98be79f975d2ad9df07` include it; #2565 ingress passed 39/39 on both Python versions. The exact mismatch and Core-owned port/rebase request were posted on #2576 and #2563. No Perception source fix is required for that stale #2576 copy.

## Research

R-196 records a full review of Gazzaev et al., *Hidden Messages Between Diffusion Language Model Agents: Causal Evidence for Latent Communication*, arXiv:2610.28905 (2026-10-20). The study finds that late transfer can outperform recurrent exchange when agents can mature evidence independently, while early query/reply is necessary for sequential dependencies. This supports V14's dynamic graph and event-driven handoff hypothesis, not a fixed A→B→C pipeline. The diffusion adapter is task-specific and not directly portable to the autoregressive runtime. Model checkpoints are stated Apache-2.0 and QASC CC-BY-4.0; linked code repository license was not verified; nothing was reused.

## Next step

Close exact-head CI for `6d3cf4a874462be3cbf250d1b566ff1c7cabde48`. Then run a source/session-disjoint native GGUF cohort only with an already-authorized pinned model; no download or production swap is authorized. Core owns the #2576 source rebase; QA owns Android consent/lifecycle proof. Keep B3 OFF until real receiver consumption and task utility are demonstrated.
