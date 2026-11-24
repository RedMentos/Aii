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


## Research note R-134 and exact CI feedback

- Full-text review and OSS/license audit recorded append-only as R-134 in V14_RESEARCH_LEDGER.md: V-JEPA 2.1's dense context-token loss and 80M distilled ViT-B are a possible future A3 feature-extractor benchmark, not an approved model swap. No weights or dependencies were downloaded.
- On prior exact head ff69ee44, frame-ingress CI on Python 3.13 and 3.14 each reported 50 passed / 1 failed. The only failure was the new registry test using per-frame receipt identity where the test intended one stable session-consent receipt; fixed by adding session_consent_receipt_ref to the fixture in commit 72dad941f0065a3308fcb48cda38207c66e0a258.
- On ff69ee44, vision-source-lineage passed on Python 3.13 and 3.14. The A5 UI lease jobs failed on the Core-owned staged source-lifecycle candidate at source_lifecycle_lock_integration_candidate.py:172: unsupported lifecycle source: vision.py. This is not a frame-ingress test failure and remains a Core integration blocker.
- The exact 72dad941 head has a new full PR matrix queued/in progress at this checkpoint; no new PASS is claimed until readback completes.
