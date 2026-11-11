# Perception handoff — 2026-11-11 23:00 Europe/Berlin

Owner: Research & Perception. Parent: PR #1798 (SQLite restart regression), no edits to other agents' branches.

## Change
Added deterministic A4 acoustic onset salience on already-validated A5 RMS frames. The `audio_views.acoustic_views` SHADOW response now exposes `a4_salience` alongside B1 detail, B2 energy gist and JEF control. Salience ranks positive RMS jumps, caps 8 events, returns chronological timestamps, and does not infer speaker, speech, intention or permission. A3 teacher/student remains UNAVAILABLE.

## Evidence
Three standalone Python unittest cases were actually executed in a local Linux Python environment: PASS (onset order, silence, invalid inputs). Source files were created on GitHub. The complete repository integration suite, production Store restart and Redmi Termux tests have **not** been executed. Local git clone still fails DNS resolution of github.com. No microphone capture or Android action authority. No model weights changed.

## Next
Run `cd v13/code && python -m unittest tests.test_audio_salience tests.test_audio_sqlite_restart tests.test_audio_store_bridge -v` in checkout/CI. Confirm existing consumers tolerate additive `a4_salience` field. Feed validated salience into C2/JEF as non-authoritative evidence only after Core interface review. A3 actual training/export and Android microphone require independent verification. Android RAM/latency UNVERIFIED.
