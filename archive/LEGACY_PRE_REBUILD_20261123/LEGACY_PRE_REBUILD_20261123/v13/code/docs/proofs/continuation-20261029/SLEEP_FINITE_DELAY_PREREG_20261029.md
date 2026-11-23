# Sleep/Dream user-delay finite scheduling — preregistration 2026-10-29

Parent checkpoint `1790d4ad20226d4feaeb4cd211e712819380a2d6`.
No Canon, Age0, model or cohort change.

## Observed problem and expected behavior
`SleepRuntime.request(mode, delay_s)` computes
`clock()+max(0.,float(delay_s))`. Python's `max(0., NaN)` evaluates
to zero, so an explicit `:sleep in nan` user delay can silently become an
immediate scheduled job. Negative delays also silently become immediate.
Scheduling must refuse nonfinite/negative delays and nonfinite due times
**before** `scheduler.post` or `tick` can run. Keep valid finite zero
and positive delays unchanged. No autonomous sleep is enabled by this patch.

## Tests before CI
- Direct request rejects NaN, ±Infinity, negative, malformed strings and
  a finite delay whose addition to clock would overflow.
- `:sleep in nan`, `:sleep in inf`, `:sleep in -1` reject without
  creating a timer, waking coordinator or changing queue state.
- Valid finite positive request still posts exactly one TIMER with origin USER,
  due = clock + delay, and triggers the existing tick once.
- Existing Sleep scheduler, policy, replay and age tests remain passing.
- Focused software CI, Canon blob, privacy/diff/compile checks and closed
  SHA256SUMS raw; preserve failed attempts.
- No STEP2/B3/Body-JEPA/LP3/World-JEPA/Redmi gate promotion.
