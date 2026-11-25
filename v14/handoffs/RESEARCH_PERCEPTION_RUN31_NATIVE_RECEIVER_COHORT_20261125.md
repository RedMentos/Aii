# Research & Perception — Run 31
**Date:** 2026-11-25  
**Started:** 23:02:26 Europe/Berlin  
**Checkpoint written:** 23:11 Europe/Berlin  
**Branch:** `research-perception/v14-anchor-preserving-tokenwise-20261125-run22`  
**Parent PR:** [#2511](https://github.com/RedMentos/Aii/pull/2511)  
**Release:** NOT_RELEASED

## Implemented

The Perception-owned native receiver task-utility evaluator now rejects duplicated source-content SHA-256 values across distinct task groups. This prevents repeated prompts from one source from being counted as independent bootstrap samples.

It also requires a crossed session × task-family cohort: every observed session must contain every observed task family, with at least `min_tasks_per_session_family` tasks per cell (default 1). The result reports the full cell-count matrix, source-group count and whether crossed coverage is satisfied. Existing eight-condition pairing, receiver/model/binary binding, per-session/per-family minima and authority-zero receipts remain intact.

Files:
- `v13/code/v13/native_receiver_utility.py`
- `v13/code/tests/test_native_tokenwise_pairing.py`
- `v14/V14_RESEARCH_LEDGER.md`

Commits:
- Evaluator: `006ec09afee1dbe40da7f16630456d698c072087` (follow-up to `635a6bc09f3ef5e268aa7037f327092a49b5f92d`)
- Tests: `cabcff089abcfb0eefe3c32bf1f11385ec56fc3d` (follow-up to `4b8fb872ce43c01f0363f718ce21486498ced721`)
- Research ledger: `d55734f8354abc62295c93645d9fdc2592b8ea12`

## Test evidence

- **LOCAL_LINUX — CPython 3.13.5:** isolated reproduction of the new cohort gate, 4 assertions PASS (normal crossed cohort, per-cell minimum, duplicate-source rejection, missing session/family cell rejection).
- **LOCAL_LINUX — full repository:** BLOCKED / NOT_RUN. No Aii checkout is mounted and `git ls-remote https://github.com/RedMentos/Aii.git` failed because GitHub DNS is unavailable in this runner. No exact repository pytest or native llama.cpp build is claimed locally.
- **GitHub Actions:** follow-up code/test head `cabcff089` has deployment-integrity PASS (Python 3.11/3.14, run 45711165841) and staged-runtime + integrated-regression PASS (run 45711165776). The integrated job ran `tests/test_staged_integrated_regression_20261111.py`: 424 passed, 3 skipped, 58 subtests passed, 6 warnings. This is not proof that `v13/code/tests/test_native_tokenwise_pairing.py` itself ran; no dedicated exact-head tokenwise adapter-contract run was observed. The earlier code/test head `4b8fb872` also completed staged/integrated + deployment-integrity successfully.
- **TERMUX/REDMI:** REDMI_UNVERIFIED. No connected device, live microphone, native GGUF target-score cohort, model download/swap, update request, restart or permission/data mutation occurred.

## Actual consumer and user effect

Core PR [#2515](https://github.com/RedMentos/Aii/pull/2515) is the intended consumer and its head branch does contain v13/code/v13/native_receiver_task_score.py, which imports and calls evaluate_native_receiver_task_utility after all eight conditions are collected. The head also contains an older helper copy (blob ec3247a6a39ec0316388961507ed76dcae873bba), not the latest Perception helper blob dcf25ba15e5a3e0e2fe1c6cb34a26cc9e1e840a6. The PR head branch is core/v14-native-target-score-20261125-run1 at d63a9d0; it diverged from the Perception branch with merge-base 68ce8ca8122fba9b0063a4da89a117377a1b9e92 (Core 43 behind / 67 ahead). Its base branch core/v14-tokenwise-native-receiver-consumer-20261125-run1 does not contain the helper, but the #2515 head does. Thus the collector is wired to an older evaluator snapshot, not the new source-disjoint/two-per-cell gate. Perception opened child PR #2516 against the #2515 head; it replaces the helper, adds collector-level tests for duplicate source and 1/9–9/1 session/family controls, and extends workflow path/branch filters. #2516 is mergeable and read back, but no exact-head CI run has been observed yet. Core review/merge is required before claiming the latest gate is integrated.

The change improves the validity of the eventual B3 native-receiver likelihood comparison. It does **not** establish semantic understanding, generated-answer correctness, trained cross-model latent coupling, production B3, model learning or a user-visible chat improvement. B3 remains OFF.

## Whole-system status carried forward

The successful integrated-regression log printed `JEPA_HOLDOUT` before=0.9685428667, after=0.9142360215, delta=-0.0543068452. The test suite passed because the holdout gate correctly rejects this regressed update; this is not a successful JEPA learning/retention result. JEPA/Memory must change the update/replay mechanism, not relax the gate.

- The P0 basic-chat / B1-B2 delivery blocker in #1904 remains open; this Perception change does not solve it.
- The tokenwise path is still a diagnostic candidate. Symbolic source-exact exchange remains distinct from learned native latent communication.
- Android device control, RAW EAR live microphone capture, persistent model-weight learning and native Redmi acceptance remain unverified.
- The last available private V13OBS #115 snapshot is historical (2026-11-24) and reported STOPPED_BY_USER; no fresh authenticated receipt was obtained in this run. Do not restart or update the device.

## Research notes / 22:00 digest

### JEPA and world models
No newly published JEPA result was verified since the previous daily digest. The full-text TD-JEPA study (Bai & Xiong, arXiv:2607.25337, 2026-07-28) remains relevant: it mines directed step-count supervision from reward-free trajectories and uses the learned temporal cost for planning. In its locked four-environment evaluation, Two-Room success is 100.0% vs 97.4% for LeWM and OGB-Cube is 82.2% vs 68.0%; the work is an offline-RL/planning study, not a general Android world model. Its public reproduction repository is CC BY-NC 4.0, so it is not a direct commercial-code reuse candidate.

### Continual learning and plasticity
- RASP (Liu et al., arXiv:2611.03513, 2026-11-02; full text reviewed) supports full forward reading with sparse backward updates in a fixed-size LoRA on four visual class-incremental benchmarks. It reports a constant 0.25–0.35M adapter budget and 3-seed results, but fixed-rank saturation and within-session near-duplicate collisions remain. It is not an LFM2.5 or Android result; no code/weights were reused and no separate implementation licence was verified.
- Stability Does Not Mirror Plasticity (Peng et al., arXiv:2611.23427, 2026-11-17; full text reviewed) finds task-dependent module preferences in a 25M synthetic transformer and Qwen2.5-0.5B: attention QK/VO learn procedural tasks more readily, MLP learns factual recall more readily, while retention order differs. The results argue for measuring acquisition and cross-task retention separately, not a universal QK/VO/MLP policy. No code/weights were reused.
- Concrete V14 test: task-family-stratified, source-disjoint cohorts before interpreting native-receiver utility; then compare module-specific update masks with matched parameter budgets and old-task retention.

### Memory and mobile execution
The module-level paper's distinction between declarative storage and attention-mediated access is a testable memory hypothesis, not a one-to-one map of human brain modules. The Android llama.cpp packaging project is MIT at repository root and targets Snapdragon 8 Gen 3 / 7+ Gen 3. Its latest repo release is v1.0.0 (2026-11-13), with API 34 / ARMv8.6-a OpenCL metadata and selected Hexagon kernels; upstream llama.cpp had advanced to signed commit b12682 on 2026-11-24. It remains an unvalidated target-device reference, not a Redmi binary candidate. It is not a validated Redmi target binary. No binary/model/weight download or swap was made. Current handset RSS/PSS, TTFT and thermal measurements remain unavailable.

## Next executable step

Core should rebase #2515 onto the updated #2511 head, implement the remaining seven condition producers with unique source/session-bound task records, then run a pinned real GGUF target-logprob cohort on LOCAL_LINUX. Minimum acceptance remains 20 unique source groups, two sessions, two task families, at least five tasks per session, four per family and crossed session × family coverage; the evaluator still requires all eight conditions per task. Keep B3 OFF until native utility beats every control with held-out evidence and independent review.

**User action: keine Aktion nötig.**
