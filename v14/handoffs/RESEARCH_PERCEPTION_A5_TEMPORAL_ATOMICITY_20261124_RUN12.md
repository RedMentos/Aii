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


## Final checkpoint — exact head and device receipt (2026-11-24)

- Perception branch head at this checkpoint: 97dfd425eb380837951af874cb3b44f3c0362a3d. The added reset negative control is included.
- Exact-head CI is still running at this read. Its frame-ingress 3.13/3.14 runs have completed successfully; the parent 26d1507 exact run established 51/51 on each Python version. The fresh 97dfd 3.13/3.14 results must be read before calling this head green.
- Parent 26d1507: vision-source-lineage 39/39 on Python 3.13 and 39/39 on 3.14; privacy and offline-bridge-security PASS. A5 UI lease 17 passed / 1 failed / 5 subtests on both versions, staged-runtime 19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests, integrated-regression failed. All converge on Core-owned source_lifecycle_lock_integration_candidate.py:172 rejecting vision.py.
- The tracked vision.py file SHA-256 was independently computed from GitHub-read bytes and exactly matches the builder's PINS value 350573e65eb445b8b83f5517e3bfe07ece04e036055c55fc3e23c79d5b0cc728. The same Git blob (2a8fce618230544ee389ac77f62e6a201e514965) is present in #2463, #2465 and #2469. Core should instrument the staged source path/actual bytes; do not weaken the pin.
- Latest available private device receipt: Aiiii #115 updated 2026-11-24 09:28 UTC reports installed 8d93236c753f0194224c19edc7411d8d7082b1d6, auto-update enabled, runtime/dashboard UP_TO_DATE; short C3 turn 358 admitted tokens, 7 generated, TTFT 2.05 s, total 6.30 s, correctness UNKNOWN; B1/B2 two failures each, zero valid offers; native residency unavailable; official Age 0 and physical feature execution unverified. Fresh private read-only requests #862–864 received no authenticated response at this checkpoint: NO_LIVE_RECEIPT.
- PR #2469 is NOT_RELEASED and its candidate is not on the phone. No Android A5 capture, MediaProjection, AudioRecord, model download, weight change, permission change or user-data mutation occurred.
- Whole-system #1984 and shared V14 work-board/Next Action remain Boss-owned; this branch records the Perception evidence for integration, not an independent master or release claim.
