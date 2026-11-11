# Research & Perception handoff — 2026-11-11 09:00 Europe/Berlin

Parent: PR #1748 head 98f87fcb7fbc037fa5a8eb82591af8122428d6a0; team plan #1668. This branch is an isolated Android-first candidate.

## Scope
Added a bounded, fail-closed **textual Android UI observation source** adapter. It accepts only an upstream redacted, explicitly authorized Accessibility observation, validates schema/receipt IDs/field allowlist/count/size, then persists a real Store text SourceRef with kind ANDROID_UI_SHADOW. No Android AccessibilityService, MediaProjection capture, app launch, tap, typing, approval verification, or Android native evidence is implemented. A boolean in an untrusted payload is **not** a real permission check; Core/QA must implement trusted Android-side receipt validation and caller authentication before any real observations may enter this adapter. This code is therefore SHADOW and MUST NOT be connected to external input yet.

## Tests
Added synthetic roundtrip/restart test and fail-closed preflight tests; execute from v13/code:
`PYTHONPATH=. python -B -m unittest -v tests.test_android_ui_source_candidate_20261111`
`python -m compileall -q v13/android_ui_source_candidate.py tests/test_android_ui_source_candidate_20261111.py`
CI/native Redmi tests unverified until run. Source text only; no PerceptPacket, B1/B2 inference or action authority yet.

## Integration contract
Core owns Android control bridge and trusted consent receipts; QA owns Android security/instrumentation. Perception will connect the approved redacted UI SourceRef to A5 via a properly persisted EventEnvelope after those contracts are agreed. JEPA/Memory must ingest only trusted committed action-outcome rows, never UI text as action truth. No changes to frozen Runtime/Cognition/Store or Age-0/STEP2/B3 gates.
