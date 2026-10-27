# LP3 six-fact frozen-C3 heldout pilot — 2026-10-27

**Owner:** `codex/automation11c-lp3-heldout-utility-20261027`, review-only child of LP3 per-row audit PR #733 exact `3fcc3f89f4b1965f6fc656744073be008eefe460`. New preregistration commit `ef806e6f5ead08e194f37ad41be452abb2126cf3` was remotely read back **before** any runner/workflow existed. Native executable and workflow fixed at `e486ff1eb1f9dad16e7b987003868304befd2f0d` (separate from prior compatibility cohort PR #731).

## Implemented

`scripts/lp3_heldout_utility.py`: official pinned LFM2.5-350M FP32 master preflight, six synthetic key/answer training facts, twelve unseen paraphrases, cyclic wrong-source controls, zero-state and no-prefix base comparisons, 24 deterministic AdamW updates on predictor/projector only, all-answer-token CE, first-token top1, three general-knowledge retention probes, frozen base/gradient and parameter-change guards, raw JSON exclusive fsync. No model/optimizer bytes are published.

`tests/test_lp3_heldout_utility.py`: five standard-library tests for fixed fixture, leakage/identity rejection, negative attribution, retention/integrity decision and metric aggregation. Actions **40527163530** on source `ac9e12b8199bb8cfe2dca4a00a1e2207a0a0ce6f`: **5/5 PASS**, Python compile PASS, privacy **CLEAN**, diff check PASS. Prior parent PR #733 exact-head Actions **40526548340**: **15/15 synthetic PASS**.

## Native status at checkpoint

Bounded official 350M Linux-native pilot Actions **40527420680**, exact source `e486ff1eb1f9dad16e7b987003868304befd2f0d`: **FAIL** at training gradient guard, before any 24-step completion or heldout result. Full FP32 master SHA preflight and software 20 tests passed; native `NATIVE_EXIT=1`, privacy=0, diff=0. Traceback: `ValueError: Missing predictor/projector gradient` at `lp3_heldout_utility.py:231`. This is a real failed attempt, not a utility-negative cohort result. GitHub artifact `12744662983`, downloaded ZIP SHA256 `3fc467c37f92b2fe442b440c60904e626fc1ef513b92345b6c3a3d8768581004`; `NATIVE_RAW.log` SHA256 `28b48f0aca83206f12cac79cfada8b7a1588c785d55344efa90f8f2598ff6949`. Exact ZIP bytes privately backed up and read back at `/V13-Checkpoints/2026-10-27/LP3-Heldout-Failed/lp3-heldout-native-failed-40527420680.zip`. No model or optimizer weights uploaded. Preserve original source, prereg and raw failure; a separately preregistered gradient diagnostic is needed before any retry.

## Binding negative gates

LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; registered `jepa_weight=0`; Age authority 0; Redmi unmeasured; C3 live integration absent; canonical architecture and user full scope incomplete. A pilot PASS would still not promote these gates or prove AGI.

## Next exact actions

Original run failed before utility scoring. Preregister a **separate** metadata/gradient-only diagnostic to identify whether the missing gradient depends on prompt, target length or LFM architecture. Do not alter or relaunch this registered source/cohort; keep original FAIL. Continue independent scheduler/Context OS packages while diagnosing.
