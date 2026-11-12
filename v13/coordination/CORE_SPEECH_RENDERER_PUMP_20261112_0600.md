# Core C3 speech renderer consumer — 2026-11-12 06:00 CET

Owner: Core & Harness. Draft PR #1825; branch `core/v13-speech-renderer-pump-20261112-0604`, based on #1799 branch `codex/v13-core-speech-operator-20261111-2106` at `66f5500b2034b9b28a1f39d20bfc7555b0aeb98a`. Files owned: existing `speech_operator.py` plus new `speech_renderer_pump.py`, `test_speech_renderer_pump.py`, CI workflow and this handoff. No JEPA/Perception/QA/Android-control files edited.

Executable path: previously committed C3 Store output -> existing SQLite SpeechIntentQueue -> explicit enabled pump -> injected Android companion renderer -> separately injected receipt verifier -> durable RENDERED only after verification. Stop during rendering, unverified receipts and uncertain renderer failure interrupt; never auto-retry uncertain speech after restart. Tests cover OFF, successful receipt/restart, rejected receipt, mid-render stop, stop during verification and renderer exception. Second package wires `LocalSpeechHandoff.render_one` to the injected renderer with a separate per-call local opt-in, and adds a committed SQLite C3 output -> queue -> renderer -> verified receipt E2E test. This is a **synthetic injected renderer**, not native audio, ASR, acoustic learning, or an Android OS capability.

Checkpoint source commit `edbc8e17cd0696fb0184f3a2afa6feaf4b5d3cdd`; exact GitHub file readback and CI still to verify. Local standalone compile succeeded; full local pytest not run because GitHub clone DNS unavailable. CI must be checked and failures fixed. No full blueprint, native Redmi, voice quality or learning proof; SourceHandoff freeze, original FAIL gates and false whole-system flags unchanged.

Next exact command on PR head:
`PYTHONPATH=v13/code python -m pytest -q v13/code/tests/test_speech_intent.py v13/code/tests/test_speech_runtime_bridge.py v13/code/tests/test_speech_store_binding.py v13/code/tests/test_speech_operator_handoff.py v13/code/tests/test_speech_renderer_pump.py`.

Next product edge: trusted Android-side TTS companion with OS permission and authenticated completion receipts, user-visible local opt-in and interruption, followed by measured Android 13 lifecycle; independent RAW EAR, decoder/vocoder learning and duplex audio remain mandatory. Continue B1/B2/C3 adapter training/retention and JEF/T8 integration on separate owned files.
