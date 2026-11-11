# Research & Perception handoff — 2026-11-11 11:00 Europe/Berlin

Parent: PR #1760, branch research-perception/raw-ear-contract-20261111-1000.

## Functionality
Added v13/code/v13/pcm_features.py. It converts bounded PCM16LE into sample-timed 10–100ms RMS acoustic frames and a source-SHA256-bound RAW EAR packet using the existing contract. It is real numerical PCM processing, not an invented model or microphone observation. Synthetic silence, sinusoid, partial-frame and rejection tests added. No ASR, no pitch estimator, no speech detection: both probability fields are 0 (unknown), pitch None. In particular zero is NOT evidence of non-speech; consumers must treat the fields as unavailable. SourceRef is supplied by caller; not authenticated.

## Tests / gates
Python syntax checked in isolated workspace; GitHub exact-head integration unittest NOT RUN (container GitHub DNS resolution failed). Run cd v13/code && python -m unittest tests.test_raw_ear_contract tests.test_pcm_features. CPU host success, if any, is not Android proof. No real Android audio permission, audio capture, A5/Runtime, B1/B2/C3, T8 replay or speech effector. All native Android gates OFF/UNVERIFIED.

## Follow-up contracts
Core: authenticated consent receipt and Store source binding before ingesting external audio. Perception: A5 timed audio PerceptPacket persistence and B/C routing, calibrated VAD/prosody later. QA: exact-head CI and Redmi 13 Termux microphone/lifecycle/latency/RAM measurements. JEPA: provenance-preserving acoustic feature/outcome training and retention, never treat ASR as raw acoustic truth.

## Source/licensing
This feature uses only Python standard library; no external model weights, datasets or licenses added. Built against internal RAW EAR contract PR #1760 and Android Voice goal ledger PR #1668. Android-first product goal remains unchanged.
