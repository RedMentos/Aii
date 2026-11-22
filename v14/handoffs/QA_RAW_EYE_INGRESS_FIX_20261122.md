# QA handoff — RAW EYE ingress integration fix (2026-11-22)

## Scope and parent

This is a QA-owned follow-up branch stacked on Perception PR #2375, starting from parent head eb6752d3d5cd42f5f3f964b4480c7954564cb6d9. Current QA branch head: 8df8b73d3af524caecd4eb6c78291987d1eaab5b. Target/base is research-perception/v14-media-projection-raw-eye-20261122-run7. It is not a replacement for the Perception implementation and does not add a MediaProjection provider.

## Reproduced failures on parent

Exact parent code/test head f87ebac407a19c147da7eb52bc63f10e9eed25d2 failed both Python 3.13 and 3.14 frame-ingress jobs:
- Valid frame, revocation, zero-budget and A3 cases raised NameError because vision_ui_frame_ingress.py called _summary(observation) without defining or importing it.
- Wrong-receipt and cancelled-lease negatives raised the expected PermissionError, but the test provider helper issued the verifier before entering consume_projected_frame's finally block. The caller-owned bytearray therefore remained nonzero when verifier issuance failed.

Boss review confirmed the existing content-free summary helper is in a5_ui_admission_bridge.py and that the zeroization failures are ownership timing in the test/provider wrapper, not an authorization bypass in the adapter.

## QA changes

- vision_ui_frame_ingress.py now imports the existing A5 _summary helper. This preserves the metadata-only summary contract and avoids creating a second, potentially divergent implementation.
- test_vision_ui_frame_ingress.py now zeroes the mutable caller-owned frame buffer if one-shot provider-verifier issuance raises before the consumer is entered. This mirrors Core UIFrameGrant cleanup; the adapter's own finally still owns cleanup after entry.
- Added a test asserting the exact content-free summary fields, bounded length and absence of any visual/OCR claims.
- No changes to OS consent, lease issuance, receipt validation, capture permissions, action authority or learning authority.

## Verification

- Parent exact-head CI: FAIL, 11 failed / 7 passed on both Python 3.13 and 3.14.
- QA branch exact-head CI: PENDING; no local Aii checkout is available in this execution environment, so LOCAL_LINUX tests were NOT_RUN.
- Android MediaProjection provider: NOT_IMPLEMENTED / OFF.
- Redmi native screen capture or UI-control proof: REDMI_UNVERIFIED.
- This adapter remains synthetic and accepts only a caller-owned frame plus a verified, active UIObservationLease; it does not open MediaProjection or capture a real screen.

## Acceptance still required

After exact-head Python 3.13/3.14 and integrated tests pass, Core must update UIFrameGrant.consume to call _issue_provider_frame_verifier(self.lease, self.observation, self.bundle["verify_frame"]) when the Perception consumer is present. The current Core PR #2379 has a two-argument call and will raise TypeError after the branches are combined. Provider pipe cancellation/zeroization and stop-vs-openFile race remain P1. No Android/Redmi acceptance until a real consented provider and device receipt exist.
