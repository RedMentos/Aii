# Tool-final output attribution — prospective source-only repair candidate (2026-10-26)

Owner: automation11, isolated review branch; base exact Run574 `4c804bb2c127bcc323182edaf0f1e56535930974`. No other owner's branch is modified. This is **not** the Run575 live STEP2 cohort; do not reinterpret any frozen native data.

## Reproduced source-level failure hypothesis before edits
In `v13/runtime.py`, an executed `eligibility` tool returning `UNKNOWN` or `NONE` under `tool_answer_first=True` writes `lead_final` as the *entire* answer and intentionally skips `runner.generate`. Nevertheless the unconditional success path sets `model_generated=True`, records `runner.last_metrics` and runs the C3 late-body watcher; the partial-output exception path also resets `model_generated=not direct`. This misattributes a deterministic tool response as native-generated and can import stale runner metrics or launch an unnecessary late observer. Reader-stage C3 use, if any, must not be conflated with answer generation.

## Intended narrow candidate
Correct only the no-native-answer final-tool branch: do not spawn latewatch, do not attribute output to C3, do not score stale native metrics or credit runner success, retain source/transaction/approval gates. Preserve A/B LEAD and normal native answer behavior, direct source copy and interruption semantics. Keep tool final text exactly as before. Add adversarial source-bound tests plus real `ToolStep.lead_final` checks. No model downloads or native/Redmi inference; no gate promotion.

## Required evidence and claim limit
Exact source hashes and branch diff, focused stdlib tests, original focused source regression, independent review/privacy scan, raw outputs even RED. Mark software/source-only only. No claim that STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, or Redmi UNMEASURED changed. Existing Run568 native failed workflow and original evidence are not altered. This branch must remain review-only pending independent integration.
