# Research & Perception — Run 73
Date: 2026-11-27
Started: 2026-11-27 21:31:26 Europe/Berlin
Checkpoint completed: 2026-11-27T20:52:51.128Z
Owner: Research & Perception
Repo: RedMentos/Aii
Branch: research-perception/v14-a3-ood-calibration-20261127-run72
PR: #2566 (DRAFT, stacked on #2565)
Code/test head: 2c0ab7421c079f5c64ac15ac0345b712944548db

## Priority selected
The B3 latent-transfer evidence path still lacked an example-pair-preserving control. The existing OOD donor permutation is intentionally cross-family; it changes both the donor example and task family, so it cannot isolate the effect of example pairing. This is a whole-Canon acceptance gap, not a claim that B3 is already implemented.

## Implementation
- Added ninth receiver condition DERANGED_MESSAGE to v13/code/v13/native_receiver_condition_matrix.py; schema is now v2.
- Requires a different source/task group from the same session and task family, with the same sender/receiver model, tap, adapter and token geometry.
- Added same-family, fixed-point-free, one-to-one donor permutation audit in native_receiver_utility.py. It separately reports fixed points, cross-family, external, cross-session and duplicate donors.
- Added a pairing-effect delta and new information-use statuses. Existing cross-family OOD remains separate.
- Updated native_latent_receiver.py and native C++ expected condition list/count to nine.
- Increased the bounded task-score receipt cap from 160 to 180 (20 task groups × 9 conditions).
- Updated matrix, utility and native receiver tests plus workflow branch filters.
- No production threshold, model, weight, Age, permission, persistent user data or phone state changed.

## Research
Jiaming Cheng, Subhransu Das, Rajiv Ramnath, *When Does Latent Communication Pay? A Causal Audit of Relayed KV Caches in Multi-Agent LLMs*, arXiv:2608.04893 (2026-08-05, preprint; not peer reviewed): https://arxiv.org/abs/2608.04893.
The paper distinguishes true paired cache from zero, moment-matched random, fixed-point-free deranged cache, intact-no-private cache and direct-text reference. It warns that a generic cache gain over zero does not establish example-specific transfer. Full-text methods/results were reviewed from the available paper copy; no authoritative code repository or code/weight license was verified, and no code was reused.
R-193 records the findings and limits.

## Verification
### LOCAL_LINUX
- CPython 3.13.5 isolated same-family audit-helper harness: PASS.
- Valid same-family permutation accepted.
- Cross-family, external and fixed-point negative controls rejected.
- Full local Aii checkout/pytest: NOT_RUN/BLOCKED; no checkout mounted and shell git ls-remote could not resolve GitHub.

### GitHub Actions — exact code/test head 2c0ab7421c079f5c64ac15ac0345b712944548db
- Run 46066036057:
  - Linux pinned-API build: PASS.
  - Android arm64-v8a cross-compile: PASS (compile only, not a phone test).
  - Focused receiver tests: 55 PASS on Python 3.13 and 55 PASS on Python 3.14.
  - Enclosing Python runtime job: FAIL at the separate staged source-tap test because Core-owned lifecycle validation rejects vision.py as an unsupported lifecycle source.
- Run 46066036056 — V13 runtime deployment integrity: PASS.
- Run 46066036089 — MediaProjection RAW-EYE ingress: PASS.
- Run 46066036060 — A5 visual bridge / A3 OOD: PASS.
- Run 46066036095 — shared staged/integrated: FAIL, 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests.
  - Recovery expects audio-composer Git blob 831080bceec90711bd42e0fa4eba47c669975c98, but the source changed.
  - Observer pin for v13/cognition.py is stale.
  - vision.py is not accepted by the lifecycle-source registry.
  - Two checkout migration tests receive PARTIAL instead of UPDATED.
  - These are Core/QA-owned source-lock and migration assertions; no foreign files were changed.

## Product effect and acceptance boundary
This adds a more discriminating diagnostic input to the native receiver task matrix. It does not change normal chat output, C3 prompt composition, or installed models. Status is WIRED_SYNTHETIC. There was no native GGUF/model inference, no generated-answer correctness test, no trained cross-model latent transfer proof, no Redmi hardware test, no release and no deployment. semantic_use_proven remains false.

## Device / updater
REDMI_UNVERIFIED. No fresh private owner receipt was available; the historical V13OBS #115 receipt from 2026-11-24 is not current installation proof. No device relay was issued in this run. No Android command, update, restart, model download, weight change, permission change or user-data access occurred.

## Coordination
- PR #2566 body updated with exact CI evidence and limitations.
- Shared blocker details posted to Core PR #2562.
- Run 73 summary and acceptance status posted to whole-Canon issue #1984.
- PR #2566 remains DRAFT and stacked on #2565; no merge/deploy.

## Next executable work
1. Add moment-matched random, intact-no-private and direct-text validity arms.
2. Increase same-family cohort size and add multi-seed/output-accuracy evidence.
3. Run a real native model pair only when authorized weights/runtime artifacts are already available.
4. Core refreshes Recovery → Stage → RuntimeDeploy audio/cognition/vision source pins; QA repairs PARTIAL-vs-UPDATED migration assertions; then rerun the shared gate.
5. Keep P0 #1904 open until the actual basic-chat failure is reproduced and fixed.

User action: none required.


## Related independent causal audit (full HTML reviewed)
Huixiang Zhang and Mahzabeen Emu, *Do Latent Channels Actually Communicate? A Causal Audit of Latent Multi-Agent LLM*, arXiv:2607.26773v1 (2026-07-29; preprint, not peer reviewed): https://arxiv.org/abs/2607.26773.
This audit uses four message settings—no message, current-example, other-example and receiver self-generated under matched compute—and five metrics: PS, PL, CIC, CAG and SSG. It tests Qwen3-4B/8B on GSM8K, ARC-C and MATH-500 with an A40 48GB, 16 Xeon cores and 128GB RAM. Example decompositions show that aggregate effects can hide opposing terms: Qwen3-4B GSM8K −1.00 pp overall = −6.17 pp other-example + 5.17 pp example-specific; Qwen3-4B MATH-500 +15.00 pp = +8.33 pp other-example + 6.67 pp example-specific. CAG and SSG can also differ, so a sender message may add content-specific value without outperforming a compute-matched self-generated receiver message. No mobile evidence or authoritative code/weight license was found.

Together with Cheng et al. arXiv:2608.04893v2, this means the current DERANGED_MESSAGE arm is only the first missing control. Remaining protocol work includes moment-matched random, intact-no-private, direct-text validity, receiver self-generated message, prediction-distribution PL/CIC, task-accuracy CAG/SSG, paired confidence/equivalence tests and hard masking/restoration checks. Current teacher-forced logprob is only a proxy; semantic_use_proven remains false.
