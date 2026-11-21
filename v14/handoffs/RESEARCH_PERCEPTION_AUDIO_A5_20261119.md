# V14 research/perception handoff — 2026-11-19

Source baseline: `gpt6/v13-private-remote-bridge-20261111`; V14 master dated 2026-11-19; prior P0 #1904 and full-scope #1984 remain open.

## Added
`v13/code/v13/audio_percept_bridge.py` implements a consent-checked timestamped acoustic observation contract, A5 typed packet and an actual call to the existing EnlightenedSpace.publish A_PERCEPTION/CONTROL consumer. Speech probability, pitch, VAD, non-speech label and provisional/final provenance remain separate from ASR. No raw audio or speaker identity is exported. This is an *adapter*, not a real microphone path, student A3, learned latent or speech decoder.

`v13/code/tests/test_audio_percept_bridge.py` covers 8 cases. A corresponding standalone Linux Python 3 synthetic implementation was exercised with 8/8 passing before remote commit. GitHub version differs in module import and exact source text; CI must run the checked-in test separately, no unverified green claim.

## Trust / limits
Existing EnlightenedSpace._source_binding validates text-only source refs. Audio is therefore published as CONTROL_ONLY with no source_refs rather than forged text evidence. A5 source_id and temporal fields remain returned in the typed packet but are not persisted or source-validated by the bus. Consent is a caller-provided Boolean: it is NOT an independent Android permission check. Native microphone, Android capture lifecycle, real provenance storage, B1/B2 consumer, A3 trainable projector, teacher ear, voice effector and actual Redmi latency are **UNAVAILABLE/UNVERIFIED**. No model/weight changes.

## Next E2E
Core/QA: bind a real Android permission service and verified audio source registry; persist the packet with event and generation checks. Perception: add verified audio SourceRef support to store and bus, then A3 acoustic projector with numerical update + heldout tests. JEPA: consume source-bound features and actual action/outcome without interpreting provisional labels as truth. Boss: only integrate after independent review and CI; release status NOT_RELEASED.

License: new glue code authored for this repo; Python standard library only; no external model, weights, OSS dependency or ARM native binary introduced. Android ABI not tested.