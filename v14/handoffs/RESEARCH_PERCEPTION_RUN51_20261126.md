# Research & Perception — Run 51 (2026-11-26)

## Checkpoint
- PR: [#2540](https://github.com/RedMentos/Aii/pull/2540) — DRAFT / NOT_RELEASED
- Branch: `research-perception/v14-raw-ear-currentparent-20261126-run52`
- Base: current Perception parent #2524, `research-perception/v14-kv-snapshot-consumer-20261126-run35`, SHA `a47907c4a0603e602581c6462ecb845211eb0445`
- Code/test SHA at PR creation: `1adf5bc8cde81fcded17590bebae189a778d3f31`
- The old #2527 branch was stale against the current #2524 parent. This new branch was created from the live parent and carries the Perception child changes without force-pushing or overwriting the parent's current native receiver, Cognition, workflow, board, workplan or coverage files.

## Implemented path
- The RAW EAR temporal evidence module now preserves monotonic accepted-window chronology across model/calibration changes and resets on source/generation changes or long gaps. Provisional windows remain reversible; FINAL windows advance committed state.
- The consent-bound PCM16 Runtime overlay connects the normal software turn to the A-plane: caller-supplied PCM16 -> timed A5 packet -> A4 voice/speaker/temporal cues -> source-bound B1/B2 context and acoustic-only C3 context.
- One `AudioConsentLease` surrounds the original Runtime turn/generator. Revocation subscription, source binding, tombstones and post-turn sweep are preserved.
- Provisional audio is excluded from C3 admission. Raw PCM is not persisted. Acoustic features are not transcript text, speaker identity, verified facts, tool authority, learning permission or OS permission.
- The A4 feature-set and predictive-closure probes remain experiments; they are not production learning or gradient/weight evidence.

## Source-pin verification
The 12 `SOURCE_BLOBS` entries in `integrated_audio_context_candidate_20261121.py` were checked against the new branch and all matched: Runtime, Cognition, audio perception bridge, voice cues, speaker evidence, temporal evidence, RAW EAR, percept contract, audio admission, percept admission, attention and contracts.

## Bug found and fixed
The previous stale #2527 head failed to import the embedded Runtime candidate because four German notice strings remained inside a Python bytes literal. Replaced those notices with ASCII text and added `test_integrated_audio_candidate_embedded_runtime_bytes_literal_is_ascii`. The earlier failing error was `SyntaxError: bytes can only contain ASCII literal characters`.

## Tests and environment
- LOCAL_LINUX isolated reproducer: `python -m py_compile` PASS.
- LOCAL_LINUX ASCII guard PASS; AST confirms the payload is a bytes literal PASS.
- Full local Aii checkout/pytest/native build: NOT_RUN. No checkout was mounted; `git ls-remote` failed because GitHub DNS could not resolve.
- Exact current-base GitHub Actions at code/test SHA `1adf5bc8cde81fcded17590bebae189a778d3f31`:
  - RAW EAR vs WebRTC/libfvad comparison: run `45900587836`, IN_PROGRESS at checkpoint.
  - RAW EAR optional NumPy backend: run `45900587850`, IN_PROGRESS.
  - A4/A5 feature-set probe: run `45900587866`, IN_PROGRESS.
  - Staged/integrated regression: run `45900587881`, IN_PROGRESS.
- The previous stale branch also had staged/integrated failures from Core-owned source pins and migration PARTIAL-vs-UPDATED assertions. Those files were not modified here and their checks were not weakened.

## Research R-170
Full-text review of Baser et al., *Latent-in-the-Middle: On the Security of Cross-Model Latent Communication in Multi-Agent Systems*, arXiv:2611.34278v1, submitted 2026-11-25 (preprint, not peer-reviewed). Three model families, four mapper families and two calibration corpora were tested. A native prompt-injection rate of 0.4% rose to as high as 44.2% after mapped-cache handoff; HandoffGuard helps on tested donors but does not stop guard-aware source fine-tuning. The study is 3B–32B/GPU work, not LFM2/Android evidence. No official code, weights or reuse licence were identified. V14 implication: foreign latent state remains untrusted and authority-zero; source authentication, model/mapper manifests, target-side safety and negative controls are prerequisites for B3.

## Device, release and user effect
- Latest available consented V13OBS #115 is historical (2026-11-24): auto-update enabled and app/runtime reported UP_TO_DATE at `8d93236c753f0194224c19edc7411d8d7082b1d6`, but AI was STOPPED_BY_USER, model process stopped, and the recorded B1/B2 attempts produced zero valid offers.
- A fresh read-only private PIPELINE_STATUS request was sent; no device receipt had arrived at the last poll. No UPDATE_REQUEST, CHAT_SEND, LOG_PAGE, shell, restart or device action.
- No model, weights, permissions, app data or installed files were changed. GitHub PR is not deployment.
- REDMI_UNVERIFIED; NOT_RELEASED. P0 #1904 basic chat and valid B1/B2 offer delivery remain OPEN.
- User effect if integrated: a permissioned PCM provider can supply time-bounded acoustic cues to the normal software Runtime without collapsing audio to ASR text. No Android microphone provider, live capture, native model run or Redmi behavior has been tested.

## Next
1. Wait for all four exact-head PR #2540 workflows.
2. If Perception gates pass, Core rebases #2538 onto #2540 and refreshes its audio-builder/recovery/source pins, then reruns staged/integrated tests.
3. Keep Android microphone/capture and real device status unverified until an authorized provider and fresh authenticated receipt exist. No user action is required now.
