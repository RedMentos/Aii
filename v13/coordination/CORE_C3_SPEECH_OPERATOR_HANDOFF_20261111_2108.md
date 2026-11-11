# Core speech operator continuation — 2026-11-11 21:08 CET

Owner: Core & Harness. Package CORE-C3-SPEECH-OPERATOR-03.
Branch: codex/v13-core-speech-operator-20261111-2106.
Base: codex/v13-core-store-speech-binding-20261111-2004, base SHA fe442e9661832e14d844ab0c5257f8fc4ef68da4.
PR: #1799 (draft, stacked on #1796 and earlier #1792/#1790).
Touched: v13/code/v13/speech_operator.py; v13/code/tests/test_speech_operator_handoff.py; .github/workflows/v13-core-speech-operator-20261111.yml.

Existing operator read-only status/stop CLI retained. Added LocalSpeechHandoff for per-call explicit opt-in from committed FINAL C3 Store output to durable SQLite speech intent queue, replay dedup, interrupt and close. Synthetic SQLite regression covers OFF, successful enqueue, stop, restart dedup and other-organ rejection. It is **not** a native Android renderer, authenticated operator identity, trained speech decoder, voice playback or user-visible autonomous speech. No changes to original model/JEPA/Body/STEP gates. Redmi UNVERIFIED.

Evidence: remote source commits f55a1467118e7ae8b257ce6e2565bac10eaf1511, 79d51a43e5ca02eae0bf4a0b43c5d0511fe1f262, 29552a722bd7506c8fe66f72a5eeac8051d5d953. Local git clone failed due github.com DNS. CI has not yet returned a run at initial query; tests NOT claimed passed.

Next exact command: `cd v13/code && python -m pytest -q tests/test_speech_intent.py tests/test_speech_runtime_bridge.py tests/test_speech_store_binding.py tests/test_speech_operator_handoff.py`. Verify GitHub Actions on PR #1799 exact head, fix red, then integrate into local operator CLI after a trusted Android-side approval design. Native companion speech renderer and acoustic training remain independent open packages. Do not merge draft into main blindly; coordinate with Boss #1788 and Perception #1798.
