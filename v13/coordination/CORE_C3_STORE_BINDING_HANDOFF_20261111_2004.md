# Core C3 committed speech Store checkpoint — 2026-11-11 20:04 CET

Owner: Core & Harness. Package CORE-C3-STORE-BINDING-03. Review PR #1796.
Base: #1792 at e2bda1227aaa609270c9437af789d5162f8aedb8; #1790 prerequisite.
Files: v13/code/v13/speech_store_binding.py, v13/code/v13/runtime.py, v13/code/tests/test_speech_store_binding.py, .github/workflows/v13-c3-store-speech-binding.yml.

The Runtime now records the actual native runner role on FINAL, model-generated, non-tool-only output. A separate opt-in Store consumer reads the committed FINAL assistant message and metadata, validates C3 origin and forwards it through the persistent speech queue with replay rejection. No auto-speaking and no native renderer or microphone permission. Existing Android control and voice learning remain OPEN/OFF. No Redmi evidence.

Evidence: source commits saved on remote; GitHub Actions workflow submitted, outcome UNKNOWN at checkpoint. Local clone blocked by DNS, no local pytest claim. Do not promote voice/audio or whole-system gates.

Next exact test: `cd v13/code && python -m pytest -q tests/test_speech_intent.py tests/test_speech_runtime_bridge.py tests/test_speech_store_binding.py`. Inspect workflow at PR #1796 head. Then attach operator-controlled opt-in Runtime invocation only after user permission, and implement independently permissioned Android renderer and stop acknowledgement. Review metadata trust and possible tool-prefixed mixed answers. Coordinate Boss integration and Perception RAW EAR; do not edit their files.
