# Research & Perception Run 78 — RAW EAR speaker-calibration self-certification guard

**Timestamp:** 2026-11-28T00:45:19.817Z  
**Repo:** `RedMentos/Aii`  
**PR:** [#2578](https://github.com/RedMentos/Aii/pull/2578) — DRAFT, NOT_RELEASED  
**Branch:** `research-perception/v14-audio-measurement-provenance-20261128-run77`  
**Branch head before this handoff sync:** `ebed8271732b8aad9e86f645944498c305173d5d`  
**Code/test commit:** `4c9bd27e56e90cba49d992c157fc5d3b4e348572`  
**Base:** #2561 `c43bd2a84f3329704b80a237bb23e61e6d614c78` → #2559 `e4795811bd3c4f43a81b71b47abcf7ea03a50a15`

## Defect and implementation

The previous provenance helper could label speaker-change evidence as calibrated when a caller supplied `threshold_status=CALIBRATED_VERIFIED`, a 64-hex digest-shaped string, a calibration ID, a numeric threshold and a non-DEFER decision. This API has no trusted calibration-receipt verifier or artifact registry, so those fields were caller assertions, not verification.

Changed `v13/code/v13/audio_percept_contract.py` so every caller-fed speaker observation remains `DIAGNOSTIC_ONLY_UNCALIBRATED`, `calibration_status=UNVERIFIED`, `identity_authority=false` until a trusted verifier is actually wired. Only the three bounded diagnostic decisions are preserved; malformed values degrade to `DEFER`. No speaker identity, calibrated probability, learning/action/truth authority or permission is added.

Added two regression tests:
1. A forged `CALIBRATED_VERIFIED` label + SHA-256-shaped value + calibration ID + threshold cannot self-promote.
2. An unhashable/malformed decision degrades to `DEFER` instead of raising or gaining authority.

### Readback blobs

- `audio_percept_contract.py`: `8c737a61cc3d560cceb1c2df271fef14d32568cb`
- `test_audio_ear_voice_cues_v14.py`: `856c8631a8d810ea69e87367d31b66ef7b1abb76`
- `integrated_audio_context_candidate_20261121.py`: `e1cf98da59cfaf585f3cdcb77a1a6e0e4be12427`
- `v14-audio-feature-set-probe.yml`: `95eb92d1701d61e139ef11534dc6aa328174eadc`
- The composer now pins audio contract blob `8c737a61cc3d560cceb1c2df271fef14d32568cb`.

## Tests

### LOCAL_LINUX
- Environment: CPython 3.13.5, Linux x86_64.
- Isolated function-level negative-control harness: **5/5 PASS** (forged calibration, malformed decision, absent evidence, caller-asserted unverified evidence, invalid evidence type).
- Full local Aii checkout / repository pytest: **BLOCKED / NOT_RUN**. No mounted checkout; `git ls-remote https://github.com/RedMentos/Aii.git` failed GitHub DNS resolution. The scratch harness is not a substitute for the repository suite.

### Exact-head GitHub Actions
On the code/test descendant and current docs-only branch head:

- RAW EAR fastpath: **213/213 PASS** on Python 3.13 and **213/213 PASS** on Python 3.14; `py_compile` PASS; privacy scan CLEAN.
- Source-bound feature-set probe: **15/15 PASS** on Python 3.13 and **15/15 PASS** on Python 3.14.
- A5 frame ingress: **29/29 PASS** on Python 3.13 and **29/29 PASS** on Python 3.14.
- A4 update/retention ablation: **50/50 PASS** on Python 3.13 and **50/50 PASS** on Python 3.14.
- A5 UI lease, offline RuntimeDeploy integrity and offline bridge/security workflows: PASS. Offline RuntimeDeploy groups were 17 + 3 + 31 + 41 tests on Python 3.11/3.14.
- RAW EAR vs WebRTC/libfvad comparison: Python 3.13 PASS (9 ABI/benchmark checks + 204 audio runtime tests). Python 3.14 was still running the comparator installation / final audio test at the last poll; do not mark it PASS.
- Shared staged-runtime: **FAIL** — 20 failed, 233 passed, 10 skipped, 2 errors, 41 subtests. Root causes include Core Recovery expecting composer blob `831080bceec90711bd42e0fa4eba47c669975c98` while Perception now supplies `e1cf98da59cfaf585f3cdcb77a1a6e0e4be12427`; stale Core arithmetic `v13/contracts.py` and observer `v13/cognition.py` pins; QA migration assertions return PARTIAL instead of UPDATED.
- Integrated regression: **FAIL**, one exact failure on the same stale Core audio-composer pin. No Perception-owned focused regression failed.

Hosted GitHub Actions is Linux CI, not local Redmi evidence.

## Research

Added **R-189** to `v14/V14_RESEARCH_LEDGER.md`:
- Frenkel, Chazan & Goldberger, *Detection of actionable domain shifts in speech enhancement systems by tracking prediction uncertainty*, JASMP 2026, peer-reviewed, full text reviewed. Their detector uses a 16M-parameter SI-SDR uncertainty predictor and 100-second aggregation; useful principle (detect actionable error, not distribution shift alone), not a Redmi model candidate.
- Kaloga & Kodrasi, *Discriminator-free adversarial domain adaptation for robust speech classification*, arXiv:2611.12119, 2026-11-09 preprint, full text reviewed. Reported SER gains are benchmark-specific and use frozen ~300M encoders; not mobile-feasible.
- No code, weights, datasets or raw user audio reused. Silero VAD remains optional and its output remains a model score, not calibrated probability.

V14 mapping: A4 active attention, A5 source-bound PerceptPacket, live provisional vs authoritative audio records, and STEP 9 audio/speech. This change hardens provenance only; it does not implement continuous microphone capture or the complete RAW EAR/teacher-ear/speech-effector loop.

## Cross-lane coordination

- Comment posted on Core PR #2576: its head's ingress blob `14198bbd33b5394c787fe31b9fbce7778cbd11e0` lacks `_validate_projector_npy_headers`, while its test expects the preflight result. Current Perception #2565 source blob `8f2b6d36cf4852ecc16da6ef0ef1639a0ead3332` contains the helper; Core #2570's copied pair passed 29/29 on Python 3.13/3.14. This is stale Core source/test ancestry, not a failure in current Perception preflight.
- Comment posted on Core PR #2577 with current Perception audio hashes. Core #2577 has advanced to head `8248010cd1c077a2f53db3cd0dfc1dda972944de`, but still uses its separate older audio composer `59a6974a5b7aba8d4f55e1e9a65b2321dbe4a468`, audio contract `f3ee37426fc3e3a8cf70f8a107e7074783118a66`, and voice-cue blob `2cf44ed0b307d5970c2ba9b416bf73d8a0833aee`. Do not transplant hashes across the #2561 and #2568 ancestries. Boss/Integrator must choose convergence order; Core then refreshes Recovery → Stage → RuntimeDeploy bottom-up.

## Product and device boundary

- A5 RAW EAR provenance is **WIRED_SYNTHETIC / FOCUSED_CI_PASS**, not ACCEPTED.
- Normal-turn Runtime/C3 use, Android AudioRecord/microphone, calibrated speaker identity, calibrated speech probability and persistent voice learning remain unproven.
- Latest available private V13OBS #115 is the historical 2026-11-24 STOPPED_BY_USER snapshot. No fresh authenticated device receipt was obtained or requested in this run.
- Updater/install state: **UNKNOWN**. No UPDATE_REQUEST, CHAT_SEND, shell, restart, permission change, model/weight swap or user-data mutation.
- Redmi: **REDMI_UNVERIFIED**. Release: **NOT_RELEASED**.

## Next executable actions

1. Boss/Integrator chooses a single convergence ancestry for Perception #2578 → #2561 → #2559 and Core #2577 → #2568; no blind cherry-pick.
2. Core refreshes Recovery → Stage → RuntimeDeploy composer pins and fixes arithmetic/observer source pins; QA fixes migration PARTIAL-vs-UPDATED assertions.
3. Core ports the current Perception A3 NPY preflight into the stale #2576 ancestry; retain the negative test.
4. Perception's next audio step is a trusted calibration-receipt verifier or a low-cost source/session-bound uncertainty-drift experiment with held-out speakers/rooms/SNR and false-alarm measurements. Keep all outputs diagnostic until calibration is independently verified.
5. Only after explicit local consent and a fresh authenticated device receipt: test Android microphone/AudioRecord and the installed updater. No device action is authorized by this PR.

**User decision:** none required; no action needed.
