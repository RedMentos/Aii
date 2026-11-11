# Core C3 speech intent queue — 2026-11-11 18:04 Europe/Berlin

Owner: Core & Harness. Package: CORE-C3-SPEECH-INTENT-01.
Branch: `codex/v13-c3-speech-intent-queue-20261111-1804`; base: `codex/v13-core-envelope-integrity-20261111-1604` (#1783).
Files: `v13/code/v13/speech_intent.py`, `v13/code/tests/test_speech_intent.py`, `.github/workflows/v13-c3-speech-intent.yml`.

Adds C3 text → persistent source-bound speech-intent queue → single renderer claim → explicit acknowledgement; supports bounded capacity, restart interruption and barge-in cancellation. Text intent is **not** a waveform, TTS, speech learning or evidence of audio playback. Android microphone, acoustic encoder, vocoder, real renderer, full-duplex and native Redmi remain OFF/UNVERIFIED. No Android OS permission or model promotion changed.

Local isolated equivalent tests: 3 passed on Linux Python pytest; remote exact-source CI must be checked before integration. This branch does not modify Perception/JEPA/QA/Boss-owned files. Synthetic tests do not establish Android-native behavior.

Next exact command: `cd v13/code && python -m pytest -q tests/test_speech_intent.py`. Then connect C3 Runtime's real response provenance to `submit()` and a separately permissioned Android speech renderer to `claim()/acknowledge()`; add authenticated renderer identity, physical stop and replay/retention proof. Do not treat the Python boolean `rendered=True` as trusted Android evidence. Coordinate with Boss #1788 and Perception #1789 before merging.
