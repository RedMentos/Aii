# Research & Perception handoff — 2026-11-20 01:00 CET

Ticket: V14-005. Draft PR #2115, head 65153c7a9a8a980ef6de1b94cfc709f62298e592, base 3bc6275c3ddef4f62170224e9c3701418c149b2e.

Read-only model registry probe: consumes existing v13/code/specs/models.json and optional installed model manifest. Detects missing provenance/checksum, missing Needle Android-arm64 artifact, and installed revision mismatch. Does not download, swap, benchmark or authorize models.

LOCAL_LINUX: python -m unittest -v test_model_registry_probe.py: 4 PASS after a detected KeyError and fix; python -m py_compile model_registry_probe.py PASS. This is synthetic manifest validation, NOT native model inference. No current model weights, license texts, Android ABI runtime or real Redmi tested. Device receipt: NO_LIVE_RECEIPT; installed SHA UNKNOWN. Release: NOT_RELEASED.

To reproduce: cd v14/experiments && python -m unittest -v test_model_registry_probe.py && python model_registry_probe.py ../../v13/code/specs/models.json

Next Core/QA integration: connect read-only report to ModelManager/doctor, test against installed manifest, then benchmark native candidate(s) serially with exact weights, TTFT/RSS/quality and Android device receipt. No production swap without separate user approval. Boss owns central V14_WORK_BOARD.json and V14_USER_NEXT_ACTION.md; please record this partial proof without marking V14-005 complete.
