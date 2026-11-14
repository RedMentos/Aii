# Perception A5 bounded prompt admission — 2026-11-14

Owner: Forschung & Perception. P0 context: public issue #1904 documents 617–634-token native C3 prefill and zero generated tokens within 30s. This addition is a **non-integrated candidate**, not a fix for native latency.

New inert module: `v13/percept_admission.py`; tests: `tests/test_percept_admission.py`. Its purpose is to preserve consent, provenance, timestamp and source lineage when future A5 audio/UI/visual evidence competes for a tiny C3 context envelope. It refuses partial summaries and exposes omissions to JEF. Token count is deliberately a conservative byte heuristic, not an exact LFM tokenizer count. The caller must independently validate actual native token count and apply global prompt admission, including user and B1/B2/Memory messages.

Run from `v13/code`: `PYTHONPATH=. python -m unittest discover -s tests -p test_percept_admission.py`.

Evidence: synthetic only. Android microphone/screen permission and native feed **OFF/UNVERIFIED**. A3 learned teacher-to-student projector **UNAVAILABLE**. RAW EAR and speech decoder **OPEN**. No training, model weights, device commands or telemetry were activated.

Boss low-risk scope: additive inert contract and tests. Integration (high-risk, separate reviewed PR) must connect A5 packet production to C4/JEF and native C3 prompt admission without silently dropping current user text, and prove phone-side prefill and response delivery. No raw private conversations in public artifacts.
