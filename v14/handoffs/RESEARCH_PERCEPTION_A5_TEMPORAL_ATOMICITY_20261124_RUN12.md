# Research & Perception — A5 temporal visual atomicity — 2026-11-24 run 12

## Defect and hypothesis

The current RAW EYE frame consumer updated the process-local temporal visual registry and persisted A4 attention modulation/requests before validating the final PerceptPacket or confirming that the active A5 context consumer accepted it. A downstream exception could therefore leave an unconsumed frame as the next frame's temporal baseline and prime A4 despite no delivered packet.

Hypothesis: prepare temporal evidence against a private copy, commit it only after packet validation and successful context delivery, and defer A4 writes until after that commit. A stale concurrent frame or revoked session must fail closed.

## Implementation

- vision_temporal_evidence.py: adds prepare_update() / commit_update() tickets, private copied state, per-session version checks and reset/LRU invalidation. Existing update() remains a synchronous prepare+commit compatibility API.
- vision_ui_frame_ingress.py: prepares temporal deltas without mutating registry state; removes cached packets and rejects stale/revoked commits; runs A4 gain/perception writes only after successful A5 context delivery.
- test_vision_ui_frame_ingress.py: adds stale-ticket/concurrent-commit and injected context-delivery failure regressions. The failure case asserts no temporal baseline, no cached packet and no A4 controller are left behind; the next valid frame must be WARMUP.

## Verification boundary

- Exact code/test source is committed on the Perception branch; exact-head GitHub Actions must run before the change is considered tested.
- LOCAL_LINUX full Aii checkout/tests: BLOCKED / NOT_RUN; no checkout is mounted and git ls-remote cannot resolve github.com.
- No Android/Redmi MediaProjection provider, APK, microphone, model, weight, permission, updater or user-data operation was performed. REDMI_UNVERIFIED.
- This is A5 frame-state failure atomicity, not a trained visual model, native latent transfer or whole-system acceptance.

## Integration

- Parent Perception session-receipt contract: PR #2469.
- A3/source lifecycle composition remains Core-owned in PR #2465. Its branch currently targets #2463 rather than #2469; rebase/compose it with this session-receipt descendant before the combined staged/integrated matrix. Preserve the exact vision source hash and the optional authenticated session receipt.
- Whole-system epic: #1984.
