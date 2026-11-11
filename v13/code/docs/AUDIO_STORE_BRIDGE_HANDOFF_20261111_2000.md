# Perception handoff — 2026-11-11 20:00 Europe/Berlin

Owner: research-perception. Parent: research-perception/audio-e2e-smoke-20261111-1900 (#1791).

## Code
Added `v13/audio_store_bridge.py` read-only production Store.one packet-table adapter. It reloads persisted A5 acoustic packet, checks packet/event/generation identity, invokes production Store.read_source (content hash/revocation), checks the A0 PCM descriptor, refuses training/native receiver authority and derives bounded B1/B2/JEF SHADOW views. This is a real Store API consumer, **not** a B/C model invocation. Added three synthetic fixture tests for replay, source revocation/hash mismatch, event identity and forged training authority.

## Evidence
GitHub files committed; **no executed tests** because local github.com DNS resolution failed, and GitHub connector cannot execute Python. Test command: `cd v13/code && python -m unittest tests.test_audio_store_bridge tests.test_audio_e2e_smoke -v`. Tests use a Store.one-shaped fixture; actual SQLite Store restart, event provenance, real B1/B2/C3 runtime, Android capture and native Redmi metrics remain **UNVERIFIED**. Do not promote A3 or Android gates.

## Integration next
Core: call replay_acoustic_packet only from approved read-only A5 replay and map SHADOW views to B/C observation contracts. JEPA: do not train from missing pitch/voice probabilities or shadow-only packets. QA: execute tests, then real SQLite Store lifecycle with persisted A0 descriptor and restart; verify actual Redmi mic permissions separately. Preserve Android-first and independent OS capability gate. Full duplex/speech effector and A3 student/teacher remain open.
