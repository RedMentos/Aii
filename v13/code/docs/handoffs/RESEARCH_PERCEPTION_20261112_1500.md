# Research/Perception handoff — 2026-11-12 15:00 CET

Base: research-perception/a5-audio-consumer-20261112-1400 (#1844).

Added a strict, opt-in SHADOW consumer wrapper `checked_audio_integrity_view`. It rechecks derived A3 feature digest against exact stored RAW EAR features, validates finite and bounded RMS/ZCR, embedding and A4 score, and performs a final source re-read. This closes the prior acceptance of arbitrary 64-character feature hashes in the consumer view. No canonical A5 promotion, B/C model inference, Android permission, ASR, or hardware proof.

Six focused tests written. Six PASS in a local Python isolated mirror with stub Store/source-gate and faithful FeatureObservation canonical serialization; exact repository dependency integration and CI **UNVERIFIED**. GitHub connector fetched current base modules; direct git clone unavailable (DNS). Tests MUST be rerun on exact PR branch before merge.

Important: source digest checks do not authenticate the A3 embedding as an actual projector result. This remains a non-authoritative view; independent A3 model receipt and canonical A5/B/C contracts are OPEN. Full Android microphone, voice, consent and native Redmi proof remain OFF/UNVERIFIED.

PHONE_RELEASE_TRAIN_2026-11-12.md and SYSTEM_CAPABILITIES_ANDROID_VOICE_2026-11-11.md returned 404 on default branch; coordination details not fully verified. Boss/Core should reconcile canonical A5 ingestion, QA Android microphone permissions, JEPA trusted experience, and release train. No external model/license added.
