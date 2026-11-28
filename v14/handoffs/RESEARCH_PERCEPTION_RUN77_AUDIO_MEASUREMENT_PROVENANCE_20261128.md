# Research & Perception Run 77 — RAW EAR measurement provenance

Date: 2026-11-28
Run start: UNKNOWN
Checkpoint: 2026-11-28 01:02:40 Europe/Berlin
Owner: Research & Perception
PR: https://github.com/RedMentos/Aii/pull/2578
Branch: research-perception/v14-audio-measurement-provenance-20261128-run77
Exact code/test head: 45505fe83803c843d2a6c77cbbc16b56102b81f4
Base: PR #2561 branch at c43bd2a84f3329704b80a237bb23e61e6d614c78 (itself stacked on #2559)
Release: NOT_RELEASED
Device: REDMI_UNVERIFIED

## Product change

The canonical A5 audio PerceptPacket now carries v14.audio-measurement-provenance/1. It separates:
- RMS/ZCR computed from the supplied PCM16 window (RMS is not SPL-calibrated);
- autocorrelation F0, voiced fraction and prosody estimates (heuristic/uncalibrated);
- rule-based activity class/score (not a probability);
- optional Silero VAD model scores (not calibrated probability);
- speaker-change diagnostics (never speaker identity);
- unavailable calibrated speech probability and ASR transcript.

The A5 → A4 → C3 path now includes cue_prov=HEURISTIC_UNCAL in the bounded C3 admission summary. Provisional VAD is marked NOT_ADVANCED_PROVISIONAL. Learning/action/truth authority remains false/zero. No raw PCM, transcript, embedding, model, weight, consent or permission changes.

## Files changed

- v13/code/v13/audio_percept_contract.py — provenance schema and default unavailable entries.
- v13/code/v13/audio_voice_cues.py — enriches the runtime packet after validated cue extraction and exposes a compact C3 provenance marker.
- v13/code/tests/test_audio_percept_contract.py — baseline packet provenance assertions.
- v13/code/tests/test_audio_ear_voice_cues_v14.py — A5/A4/C3 provenance assertions plus optional/provisional VAD regressions.
- .github/workflows/v14-raw-ear-fastpath.yml — compiles/runs the contract and integration tests.
- .github/workflows/v14-audio-feature-set-probe.yml — refreshes exact source blob pins.
- v13/code/scripts/integrated_audio_context_candidate_20261121.py — refreshes Perception-owned composer pins.

## Evidence

LOCAL_LINUX isolated scratch module/packet harness:
- py_compile: PASS
- 7/7 tests: PASS
- Covers default unavailable fields, heuristic non-probability labels, VAD model-score provenance, provisional VAD not advanced, malformed input rejection and speaker-identity authority rejection.
- This is an isolated scratch reproduction, not the full Aii checkout or repository test suite.

Full local Aii checkout / pytest: BLOCKED / NOT_RUN (no mounted checkout; GitHub DNS resolution failure).
Earlier code head 3ff5e: RAW EAR fastpath PASS Python 3.13/3.14 and feature-set probe PASS Python 3.13/3.14. Current code/test head 45505fe: RAW EAR fastpath pending, feature-set queued, RAW EAR/libfvad comparison queued, staged regression queued, RuntimeDeploy queued; no current-head pass claimed.
Shared staged/integrated: not observed for #2578; previous #2561 Core/QA-owned pin/migration failures remain open.
Android/Termux microphone, normal-turn Runtime/C3, device lifecycle and Redmi: REDMI_UNVERIFIED; no device action or live receipt.
Updater/deployment: not queried or attempted; NOT_RELEASED.

## Research R-188

Full peer-reviewed paper: “Analysis and Calibration of Lombard Effect and Whisper for Speaker Recognition,” IEEE/ACM TASLP, 2021-01-21, 29:927–942, DOI 10.1109/TASLP.2021.3053388, https://pmc.ncbi.nlm.nih.gov/articles/PMC9245507/. Six corpora and condition-aware score calibration support separating raw detector scores from calibrated decisions. This is not a VAD-probability calibration result and does not validate RAW EAR's heuristics.

Official Silero VAD README inspected 2026-11-28: https://github.com/snakers4/silero-vad . Repository advertises MIT, ONNX Runtime support and edge/mobile use. Exact ONNX artifact license/revision and ARM64/Redmi performance were not independently verified. No model/code/weights were reused or downloaded.

## Cross-lane blocker

Core recovery candidate still expects composer blob 831080bceec90711bd42e0fa4eba47c669975c98; current Perception composer blob is d51b0436ed6a50cb264eb57a40eafe66ee202143. Staged integration also reports separate stale arithmetic/observer pins and two QA migration assertions returning PARTIAL rather than UPDATED. Core/QA ownership is preserved.

## Next action

1. Observe exact #2578 focused RAW EAR and feature-set workflows.
2. Fix only Perception-owned failures; do not mask Core/QA staged failures.
3. Boss reviews the stacked contract.
4. Core refreshes Recovery → Stage → RuntimeDeploy audio-composer pins.
5. QA keeps microphone/provider capture OFF until Android consent, lifecycle, revoke, restart and rollback are verified on authorized hardware.
