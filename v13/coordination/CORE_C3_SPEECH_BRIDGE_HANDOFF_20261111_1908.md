# Core speech runtime bridge checkpoint — 2026-11-11 19:08 CET

Owner: Core & Harness; package CORE-C3-SPEECH-BRIDGE-02.
Base: #1790 at 055dd6c920d97b62e07e43a10682e5f502bbf9e6.
Branch: `codex/v13-core-speech-runtime-bridge-20261111-1908`.
Changed: `v13/code/v13/speech_runtime_bridge.py`, `v13/code/tests/test_speech_runtime_bridge.py`, `.github/workflows/v13-c3-speech-runtime-bridge.yml`.

Implemented an explicit opt-in C3 completed-response receipt to persistent text speech queue. The bridge checks event format, completed state, C3 role and exact text SHA256 before enqueuing, supports stop/interruption and persistence after restart. It does not hook Runtime's authoritative completed output yet; callers could forge the Python receipt, so this is **not** an authenticated native provenance boundary. No waveform/audio output, Android native execution, permission grant or active learning promotion. Native Redmi UNVERIFIED.

Tests added for opt-in, queued/claimed/stop/restart and rejected incomplete/tampered/other-organ receipts. Local git clone unavailable (DNS resolution of github.com failed); **no local pytest execution** and CI outcome pending. The branch is a draft, not production integration. Preserve all Canon negative gates.

Next exact command: `cd v13/code && python -m pytest -q tests/test_speech_intent.py tests/test_speech_runtime_bridge.py`; inspect CI at the branch HEAD. Then bind receipt generation to actual committed C3 Runtime output, not a caller-supplied flag; implement Android-side authenticated renderer/stop, independent OS permissions, and audio decoder separately. Coordinate with Perception #1791 and Boss #1788, do not edit their files without agreement.
