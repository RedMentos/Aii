# Research & Perception handoff — Teacher Ear descriptor pinning

- Date: 2026-11-24; run 32
- Branch: `research-perception/v14-audio-duplex-bridge-20261123-run21`
- Candidate code/test head at checkpoint: `7ba3fec3f016e770f1280af5f190d1a9fa0def6a`
- PR: #2448, OPEN / DRAFT; base `gpt6/v13-private-remote-bridge-20261111` at `8d93236c753f0194224c19edc7411d8d7082b1d6`; NOT_RELEASED

## Implemented

- `v13/code/v13/audio_teacher_ear.py`: secure root/parent traversal via directory FDs and `O_NOFOLLOW`; hash already-open files; verify `/proc/self/fd` inode identity; retain descriptors across the native `OnlineRecognizer.from_transducer` call; explicit `SherpaOnlineTeacher.close()`.
- `v13/code/tests/test_audio_teacher_ear.py`: final-file replacement, parent-directory symlink swap, native-loader path pinning, close behavior and updated symlink rejection contract.
- `v13/code/tests/test_audio_speaker_evidence.py`: corrected schema-v3 consent-epoch state key and non-voiced interpretation expectations.
- `v13/code/tests/test_audio_teacher_ear_runtime_integration.py`: provisional stream hypotheses remain packet-bound but excluded from C3; only the FINAL revised hypothesis is admitted.
- `.github/workflows/v14-raw-ear-vad-comparison.yml`: refreshed exact source blob pins for `audio_voice_cues.py` and `audio_temporal_evidence.py`.

## Test evidence

- LOCAL_LINUX isolated reproduction: Python 3.13.5, Linux 6.18.57 x86_64; `py_compile` PASS; 5/5 descriptor/path regression cases PASS. This was a focused reproduction of the exact algorithm, not the full repository suite.
- Exact-head CI `345de43a...`: 5 failures, 173 passed. Failures were stale schema-v3 speaker expectations/state key, Teacher Ear symlink regex, and a C3 integration test that contradicted the current PROVISIONAL→FINAL gate.
- Corrections committed in `a20ff439`, `a3d4f24`, `bf8b30f`, and `7ba3fec`; latest exact head `7ba3fec...` has new checks queued at last observation. Do not call CI green until all relevant jobs finish.
- Full repository tests were not run locally: no repository checkout and GitHub DNS resolution unavailable in the local container.

## Runtime / user impact

- Actual consumer: optional Teacher Ear `_load()` now supplies descriptor-backed paths to the native recognizer constructor. This protects path identity during the verification-to-open handoff.
- No direct chat/voice response improvement has been measured. No Android microphone/provider integration, native sherpa model load, weight learning, or device-control behavior is claimed.
- Provisional ASR text remains excluded from C3 until FINAL; the test was corrected to match that existing gate, not to relax it.

## Device, updater, permissions

- REDMI_UNVERIFIED: no handset was connected; Android `/proc/self/fd`, `dir_fd`, ARM ABI, RSS and native sherpa load were not tested.
- Private V13OBS #115 updated 2026-11-24 02:58 UTC reports auto-update enabled and dashboard UP_TO_DATE at base `8d93236...`. That does not prove PR #2448 is installed or that C3/B1/B2 are functional. The five-turn aggregate still reports B1/B2 native failures and zero valid offers; latest C3 turn generated 7 tokens with 1.87 s prefill-to-first-token.
- Read-only requests #843–#845 (HEALTH, PIPELINE_STATUS, DIAGNOSTICS) had no receipt at last check. No UPDATE_REQUEST, model download/swap, permission change, shell command or device action was issued.

## Research / licensing

- Checked upstream `k2-fsa/sherpa-onnx` at `6e24506004105319393a3cd9954a375068ef44dd`, Apache-2.0. Its Python path-based recognizer API and C API configuration were reviewed; no upstream code or model was copied.
- No new paper was sufficiently relevant to this specific TOCTOU defect; no model alternative or download is proposed.

## Next action

1. Finish exact-head Python 3.13/3.14 CI for #2448; repair any remaining real failures rather than relabel them.
2. Verify `dir_fd` and `/proc/self/fd` support on authorized Termux/Android, then test the real sherpa-onnx native loader with an explicitly approved local model.
3. Continue the speaker-history 1 s/2 s invariance and non-voiced negative-control tests; preserve RAM-only vectors and uncalibrated DEFER behavior.

User action: none. No user permission is needed for this code-only change; device/model testing remains separately gated.