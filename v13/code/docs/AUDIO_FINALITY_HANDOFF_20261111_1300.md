# Research/Perception handoff — 2026-11-11 13:00 Europe/Berlin

Base: research-perception/audio-a5-persist-20261111-1200 (draft PR #1768).
Owner: A-plane audio perception; no foreign branches modified.

## Defect
The A0 event() Store path explicitly persists only AUTHORITATIVE events, whereas build_pcm_raw_ear() defaults to provisional=True. Previously persist_audio_percept() allowed provisional frames to become a durable A5 packet without any finality check. This is a provenance/learning boundary failure, not proof of Android microphone access.

## Patch
Reject raw.provisional unless exactly False before calling store.add_packet. Existing synthetic success fixture now requests provisional=False; new negative fixture asserts provisional packets are not stored. All other gates and receiver/action/training authority remain zero.

## Evidence
Source changes committed to this branch; synthetic test authored but NOT EXECUTED or CI-verified. No native Redmi measurement. Existing tests use FakeStore; real Store + restart and C/B consumption remain required. A3 real teacher/student, voice decoder, Android microphone, UI permissions, numeric learning and OS control remain OPEN. Provisional acoustic observations need a separate SHADOW/ephemeral lane with explicit revocation/finalization, not a false authoritative event.

## Next
Run `PYTHONPATH=v13/code python -m unittest v13.code.tests.test_audio_a5` (adjust test discovery to repository runner), then real Store restart integration; verify all staged PR dependencies and exact GitHub CI. Coordinate Core for finality policy and JEPA for learning exclusion. Do not promote Age0/STEP2/B3.
