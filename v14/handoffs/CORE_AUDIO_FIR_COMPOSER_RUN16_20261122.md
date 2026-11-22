# Core & Harness — RAW EAR FIR composer integration (2026-11-22, Run16)

**Status:** DRAFT / NOT_RELEASED / REDMI_UNVERIFIED. This is a staged-runtime source integration candidate, not a phone deployment or voice-capture proof.

## Stack and ownership

- Base dependency: Perception PR #2322, branch `research-perception/v14-raw-ear-antialias-20261122-run12`, exact base head `e9a57dd9398d0e5241c1c573acdaf7d1e610515c`.
- Core baseline ported: reviewed PR #2325 exact head `389013f664f6a0ba6d1ea1aab83d9cfd17a5ea83` (Boss review recorded 18 successful checks and 2 policy-expected skips).
- Perception-owned producer/tests were not edited. This branch layers Core-owned composer and staged-runtime changes on top of the Perception branch; it is explicitly stacked and must be integrated only after the base dependency is accepted.

## Connected changes

1. Rebound `integrated_audio_context_candidate_20261121.py` from the old `audio_voice_cues.py` blob `4c5641adf6758762ce0fdf616a9b2a798e6de408` to the reviewed FIR producer blob `b18e450162b062b09368a12b1ca18924ed8c5025`.
2. Ported the current Core fair-observer budget and native sender-path containment overlays/tests from #2325.
3. Rebound the complete downstream integrity chain:
   - composer Git blob: `831080bceec90711bd42e0fa4eba47c669975c98`
   - recovery wrapper Git blob: `774bc1549b09fd207fee5007e268265fa1973bd2`
   - stage builder Git blob: `2dacbaedec29081d24fa10d3f9d144fd67706140`
   - deployer Git blob: `cf9adccc8bbce102662520dfd823a0819661d7f6`

## Exact readback checks

All seven source-pin checks passed against the exact branch contents:

- RAW EAR producer pin = `b18e450162b062b09368a12b1ca18924ed8c5025`
- recovery wrapper composer pin = exact composer blob
- recovery wrapper base-builder pin = exact base-builder blob
- recovery wrapper native-receiver pin = exact receiver-builder blob
- C4 receipt SHA-256 = exact C4 receipt source
- stage builder SHA-256 = exact recovery-wrapper bytes
- deployer STAGER SHA-256 = exact stage-builder bytes

This is a GitHub source-readback/hash-chain check, not Python execution.

## Test and device boundary

- LOCAL_LINUX full repository suite: **BLOCKED** — no Aii checkout was available; `git ls-remote https://github.com/RedMentos/Aii.git` failed because this container could not resolve `github.com`.
- Focused source-pin readback: **PASS**.
- Exact branch GitHub Actions: **PENDING** until the PR is opened and workflows finish.
- Native llama.cpp/GGUF execution: **NOT_RUN**.
- TERMUX/REDMI: **REDMI_UNVERIFIED**. No phone receipt was requested or obtained; no UPDATE_REQUEST, model/weight/permission change or device action occurred.
- Audio remains caller-supplied PCM16 only. No Android AudioRecord, microphone permission, speaker identity or speech decoder is added.

## Next executable step

Run exact-head staged-runtime, integrated-regression, native-receiver and privacy checks; fix any failures on this branch and retest. If green, Boss can integrate the stacked Core change after #2322 is accepted, then update the shared user-next-action record. Preserve B3 production routing and training authority at zero until separate native/semantic acceptance.
