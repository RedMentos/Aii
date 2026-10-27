# C1/JEF goal-sequence event provenance — verified RED/GREEN checkpoint (2026-10-27)

Review-only child of PR #776, parent `1d0ab1ca8cf64f7d2d4f9e313ca39e87bf2370c5` (not main). Prereg commit `ed24839630b1c7da77c4ef683deebdf995192e85` predates RED test commit `92f1e8546e4ee860de34e4fe9793e385ec7f80b1` and source fix `932e2a08589fa94b9b2e5b77c1afebae1ce287b4`.

## Proven failure and narrow fix

Persisted `goal_sequence` previously required only a hash-valid source, allowing a cross-session event or a mismatched same-session event/source to enter `effort_context.prior_goals`. A forged event ID with a valid source was also retained. New `Executive._goal_valid` binds each history item to an existing authoritative event in the same session with the exact event source; malformed and mismatched items fail closed. Genuine two-turn history is preserved. This is not a claim that C1 learned semantic continuity or that native output quality improved.

## Closed focused evidence

- **RED Actions 40587974925**, expected FAILURE: 16 tests, 3 new failures (foreign session, swapped source, fabricated/malformed event); 13 pass. Original ZIP artifact `12772842091`, SHA256 `72d44d77fcfa430d7549f85a2268a921efb3b6b600f118b1b19937b928e002fa`. HEAD `3a24d00d0b1e092a12f2c5f06ecf3b37de8ddc74`, source blob `05500ee25d7cd83b3412f027e1503ca907e12d43`, test blob `86cbbb3b20a7fe11aad77802d4be1ffaf2197925`. PREREG/INSTALL/COMPILE/PRIVACY/DIFF exits0, UNIT exit1. Original ZIP CRC PASS.
- **GREEN Actions 40588131719 SUCCESS:** 16/16 PASS; all PREREG/INSTALL/UNIT/COMPILE/PRIVACY/DIFF exits0, privacy CLEAN. ZIP artifact `12772708503`, SHA256 `51e2518cfcdfa492f2a1bd926a74eeec617afbca3d5d81a368b79017bcea4cf0`; HEAD `932e2a08589fa94b9b2e5b77c1afebae1ce287b4`, source blob `e42e586b7e685cf3b0abc80a17c203bfc7dfc845`, same test blob `86cbbb3b20a7fe11aad77802d4be1ffaf2197925`. ZIP CRC PASS.
- Both original raw ZIPs privately uploaded to `/V13-Checkpoints/2026-10-27/Automation11-C1-GoalSequence/` and re-materialized with identical SHA256. This is a private native Library checkpoint, not the rejected anyone-writable Drive destination.
- **Full source-wide software workflow 40588165109:** started; result pending at this checkpoint. Do not claim it passed until raw exits and ZIP are verified.

## Status and next action

Software-only Linux/synthetic DB test; no Redmi/Termux JSON1, native model, production integration, utility or learned-gain evidence. Frozen SourceHandoff, all model/seed/cohort hashes, LP1/LP2/BJ1/STEP2/B3 negatives, jepa_weight0, Age authority0 and entire V13 canon unchanged. No shared BUILD_STATE overwrite. Independent review required; no auto-merge.

Exact focused command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_executive_goal_sequence_binding_review tests.test_executive_task_origin_binding_review tests.test_executive_source_action_integrity_review tests.test_executive_context`.

Next: close source-wide Actions 40588165109 raw evidence and publish review-only PR; then pursue a distinct roadmap package. Remaining budget UNKNOWN.
