# Core & Harness Run 51 — adaptive C4 reserve and exact source-pin chain

**Date:** 2026-11-26  
**Budget PR:** [#2539](https://github.com/RedMentos/Aii/pull/2539), DRAFT / NOT_RELEASED  
**Budget branch/head:** `core/v14-adaptive-c4-budget-20261126-run2-core` / `f0465a3644c7b1c6e22779c5dc6eb4deadcd4aba`  
**Base:** Core PR #2535 branch `core/v14-native-prompt-request-binding-20261126-run1`, base checkpoint `e00f6e0da57f94c1c5f06a103fc96bfd1bb18d54`.

## Implementation

The existing short-turn recovery planner already preserves a measured C3 output reserve and fairly divides the remaining pre-answer window between B1/B2. This change replaces only the fixed 1-second C4 focal reserve with a bounded estimate from the existing content-free `stage_marks_s.focal_loop` → `stage_marks_s.output_prepare` interval.

- Up to three recent completed C4 samples; the sample is valid even if the later C3 decode timed out.
- Estimate = max recent duration × 1.25 + 0.5 seconds; fallback 1 second.
- C4 cap = 6 seconds and 25% of the turn.
- Recovery still preserves the 6-second minimum C3 reserve and two 2-second B1/B2 attempt slices.
- Non-finite, malformed, negative, zero or implausibly long samples are ignored.
- No prompt/answer text is read. Normal/deep turns, direct/foreground paths, Age, learning rights and weights are unchanged.

The existing Runtime/Cognition caller consumes the returned `focal_reserved_seconds`; this is not a parallel scheduler.

## Pin repair after first CI

The first exact CI on pre-pin-refresh head `b852f643ec7704cf3324a383ca3cf423e997b9f6` found the expected stale observer source pin:
- new `native_turn_budget.py` SHA-256: `d84bb43c83408369375af8b50233f2fc019615b36f77f7eb87b18796ae253baf`;
- updated observer candidate SHA-256: `4b47d850ceb5ba3b1cdf40e5046085b66ee3bebdf53df0c3771c6d32323f0f3a`;
- updated recovery-composer Git blob: `b00c41e8f1e6fdab21fa0d9a4a04d8b91ba3fcac`;
- updated recovery-wrapper SHA-256: `fe766c140124eb87765b47a2ae462b8a1ddd25a80e9b2a99c2bac503856131f4`;
- updated stage-builder SHA-256: `d7e03c8d77a34f54156906865d808bc11b771f98fee4bed07f3d449d2e20c57a`;
- RuntimeDeploy `STAGER_SHA256` updated to that stage-builder hash.

The recovery composer, wrapper, stage builder and RuntimeDeploy were refreshed bottom-up. No source-pin check was weakened.

## Test evidence

- New tests cover measured C4 reserve, completed C4 followed by C3 timeout, cap while preserving both body slices, and malformed-stage fallback.
- LOCAL_LINUX CPython 3.13.5 scratch-equivalent planner reproduction: 4 new-case checks + 10 existing-boundary-equivalent checks PASS. This is not the exact repository pytest suite.
- Previous exact-head staged CI failed at the stale observer pin. That prevented RuntimeDeploy; the two migration tests consequently reported PARTIAL because runtime was ERROR while dashboard was UPDATED. The test assertions were not relaxed.
- Exact CI on replacement PR #2539 head `f0465a3` is pending; must be read back before claiming success.

## Release and device boundary

No full local Aii checkout, no exact local pytest/native build, no Redmi/Termux receipt, no GGUF execution, no install/deploy, no model/weight/permission/data changes. REDMI_UNVERIFIED; B3 OFF; P0 #1904 OPEN; RELEASE_SHA NOT_RELEASED.

## Next action

Inspect exact-head #2539 staged/runtime/migration workflows. If the pin fix clears RuntimeDeploy, verify the migration results become UPDATED (or UP_TO_DATE only where the exact target is already present) and that the active launcher receipt matches the target. Then continue the whole-canon integration path; do not treat this budget change as whole-system completion. No user action is needed for CI.
