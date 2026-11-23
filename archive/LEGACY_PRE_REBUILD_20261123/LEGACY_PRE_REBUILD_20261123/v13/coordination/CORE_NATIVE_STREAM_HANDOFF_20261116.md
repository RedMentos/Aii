# Core & Harness handoff — 2026-11-16 11:26 UTC

Owner: Core & Harness. Package: CORE-NATIVE-STREAM-INTEGRITY-20261116.
Base: phone release branch `gpt6/v13-private-remote-bridge-20261111`, base SHA `d9ffe1f3fb1646a3e7b7aa4e8e30f46e05267614`.
Branch: `gpt6/core-native-stream-integrity-20261116`. Review PR #2003.
Owned paths: `v13/code/v13/runners.py`, `v13/code/tests/test_native_stream_integrity.py`, `.github/workflows/v13-core-native-stream-integrity.yml`.
Runtime change: llama-server completion must deliver a terminal `stop:true` frame. A premature HTTP EOF after partial or zero output now raises `Unavailable` rather than allowing false `FINAL`. Existing outer `generate` failure handling unloads an interrupted runner. No permission, Age, model or source change.
Test contract: `cd v13/code && python -m unittest discover -s tests -p test_native_stream_integrity.py -v`.
Evidence: GitHub source commit/readback confirmed; local repository checkout unavailable because DNS resolution of github.com failed; connector workflow runs returned none at checkpoint. **Tests NOT EXECUTED; CI UNKNOWN.** NOT_RELEASED; REDMI_UNVERIFIED.
Related: #1904 (native chat P0), #1984 (whole canon). Concurrent Core PRs #1995, #1998 and #2001 own arithmetic; do not overwrite them. Research/Perception owns #2000/#2002.
Next exact commands: run the unittest above on the exact PR checkout, then `python -m pytest -q tests/test_native_stream_integrity.py`; review native framing and stream failure cleanup, obtain CI result, ask Boss to integrate after review. On installed Redmi correlate failed native stream receipts and B1/B2/C4/C3 actual source-bound delivery. Then proceed to other Canon families, particularly live organ coupling, audio/vision, direct bounded weight updates, Android control and restart/retention.
Negative gates: STEP2/B3/Body-JEPA native learning and full V13 remain unproven. This fix does not improve latency or prove correctness.
