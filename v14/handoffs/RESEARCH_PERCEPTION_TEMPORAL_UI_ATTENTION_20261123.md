# Research & Perception handoff — temporal RAW EYE attention

Date: 2026-11-23  
Parent: `research-perception/v14-media-projection-raw-eye-20261122-run7` at Perception code head `e21a85a329ea25a2208fcfa64edc216884b55bf1`  
Branch: `research-perception/v14-ui-temporal-attention-20261123-run1`  
PR: pending creation; stacked on the parent MediaProjection RAW EYE ingress PR #2375.

## Product gap

The MediaProjection RAW EYE consumer in #2375 turns one authorized frame into a global + 16-tile PerceptPacket and runs A4 on the current frame. It has no bounded comparison with the previous frame from the same live UI observation lease. A changed region can therefore be admitted only from its current handcrafted salience/text summary; temporal novelty is not yet a first-class A4 signal.

## Implemented

- Added `v13/code/v13/vision_temporal_attention.py`: a source/session/receipt/Runtime-generation/**lease-object**-bound registry of at most 8 streams. It retains only 16 × 37 float tile descriptors in process memory, never image bytes, text, files, Store rows or weights. It resets on source revocation through the scoped consumer and exposes an explicit reset function for the Core caller.
- Added frame-to-frame mean absolute feature deltas over the existing RAW EYE 37D tile features. A 2-second maximum gap and timestamp regression force a warm-up reset. Duplicate frame hashes produce zero change. Malformed/non-finite/out-of-range features fail closed without replacing the previous snapshot.
- Wired the result into `vision_ui_frame_ingress.consume_projected_frame`: changed tiles receive a bounded priority bonus, A4 receives a `novelty` and thresholded `external_interrupt` modulation, and A5/PerceptPacket carry the numeric change evidence.
- Added a `reobserve_proposal` for large changes. It is only a proposal: `requires_user_approval=true`, `automatic_capture=false`, `action_authority=false`, `learning_authority=false`. No additional MediaProjection capture is started.
- Added unit and end-to-end synthetic tests and extended the exact Perception CI workflow to compile and run them.

Thresholds (change 0.05, interrupt 0.08) are BOOT heuristics selected only to make the synthetic color-change fixture detectable. They are explicitly marked uncalibrated and require real-device/source-disjoint calibration before any production tuning.

## Research note

**ActiveForager — “Look Closer, Look Back, or Wait for Agentic Streaming Video Understanding,” arXiv:2611.24267 v2, 18–19 Nov 2026.** This run could inspect only the arXiv metadata and abstract; the full PDF/HTML was inaccessible, so this is not a full-paper review. The abstract reports a policy choosing direct answer, high-resolution recent-frame inspection, history recall, or waiting, trained with counterfactual information gain; results are reported on Qwen2.5-VL-7B/Qwen3-VL-8B, including OVO-Bench and Video-Holmes. This is preprint evidence, not Android evidence. No project repository, code license or weight license was verified; no code or weights were reused. The V14 adaptation here is only the inexpensive “notice a temporal change and propose another look” primitive, not an ActiveForager reproduction or trained policy.

Primary source: https://arxiv.org/abs/2611.24267

## Verification

- LOCAL_LINUX, CPython 3.13.5 x86_64: isolated module `py_compile` PASS; isolated unit tests PASS (7/7 at initial checkpoint; exact repository test adds NumPy-array acceptance and UI integration). Full Aii checkout is not mounted, so the full repository suite was not run locally.
- LOCAL_LINUX synthetic feature experiment: existing `vision.tile_features` formula (37D, 4×4 grid) on 64×64 fixture, red panel → green panel → unchanged frame: `WARMUP → MEASURED → DUPLICATE`; max tile delta 0.097093; four tiles crossed the 0.05 change threshold; interrupt signal 0.097093 crossed 0.08. Registry-only update averaged 0.1219 ms/frame over 10,000 iterations (not including image decode/PIL/NumPy/A4).
- GitHub exact-head CI: pending after PR creation.
- TERMUX/REDMI: **REDMI_UNVERIFIED**. No connected handset, Android capture, or native runtime measurement was available. This does not prove continuous capture or Android integration.

## Risks and boundaries

- This is a hand-crafted feature-delta heuristic, not semantic event understanding, calibrated uncertainty, a trained attention policy, or learned latent exchange.
- UI animations, scrolling, cursor blink and anti-aliasing can trigger change hints; threshold and gap need source-disjoint real UI evaluation.
- A new lease object deliberately starts from warm-up, preventing cross-capability comparison. Temporal continuity exists only while the same active lease/session is held.
- Core must call `reset_runtime_ui_temporal_attention(runtime, source_id)` when it revokes a lease through a direct adapter path; `consume_projected_frame_scope` already resets automatically. The new signal never authorizes another capture.
- No model, weights, dependency, permission, device state or user data were changed.

## Next executable step

Run the exact-head Python 3.13/3.14 Perception workflow. Then coordinate with Core PR #2408 so the direct Runtime caller resets temporal state on its post-C3 lease revoke and carries the proposal only as a user-approved next-observation hint. Keep the branch stacked until #2375/#2408 source composition is accepted; do not claim REDMI_VERIFIED.
