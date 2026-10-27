# LP3 six-fact frozen-C3 heldout pilot — 2026-10-27

**Owner:** `codex/automation11c-lp3-heldout-utility-20261027`, review-only child of LP3 per-row audit PR #733 exact `3fcc3f89f4b1965f6fc656744073be008eefe460`. New preregistration commit `ef806e6f5ead08e194f37ad41be452abb2126cf3` was remotely read back **before** any runner/workflow existed. Native executable and workflow fixed at `e486ff1eb1f9dad16e7b987003868304befd2f0d` (separate from prior compatibility cohort PR #731).

## Implemented

`scripts/lp3_heldout_utility.py`: official pinned LFM2.5-350M FP32 master preflight, six synthetic key/answer training facts, twelve unseen paraphrases, cyclic wrong-source controls, zero-state and no-prefix base comparisons, 24 deterministic AdamW updates on predictor/projector only, all-answer-token CE, first-token top1, three general-knowledge retention probes, frozen base/gradient and parameter-change guards, raw JSON exclusive fsync. No model/optimizer bytes are published.

`tests/test_lp3_heldout_utility.py`: five standard-library tests for fixed fixture, leakage/identity rejection, negative attribution, retention/integrity decision and metric aggregation. Actions **40527163530** on source `ac9e12b8199bb8cfe2dca4a00a1e2207a0a0ce6f`: **5/5 PASS**, Python compile PASS, privacy **CLEAN**, diff check PASS. Prior parent PR #733 exact-head Actions **40526548340**: **15/15 synthetic PASS**.

## Native status at checkpoint

Bounded official 350M Linux-native pilot workflow `.github/workflows/lp3-heldout-native-pilot.yml` launched from `e486ff1eb1f9dad16e7b987003868304befd2f0d`, Actions **40527420680** **IN_PROGRESS** at checkpoint. Maximum 20m native command, 35m job. Artifact must contain original `NATIVE_RAW.log`, `NATIVE_EXIT.txt`, source/prereg blob IDs, privacy/diff exits and `RESULT.json` if successful. **No native success, utility or attribution signal is claimed before the raw artifact and exact SHA are independently audited.** Preserve failure if timeout/crash.

## Binding negative gates

LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; registered `jepa_weight=0`; Age authority 0; Redmi unmeasured; C3 live integration absent; canonical architecture and user full scope incomplete. A pilot PASS would still not promote these gates or prove AGI.

## Next exact actions

Read Actions `40527420680` and download/audit raw artifact, verify full master SHA, prereg-before-run, train/heldout partition, 24 steps, source/answer leakage, frozen base and all preregistered thresholds. Record exact success or failure and keep original negative gates. Then independent review; a larger multi-seed study only under a **new** preregistration, no reusing the current cohort to tune thresholds. Continue independent roadmap packages while native is running.
