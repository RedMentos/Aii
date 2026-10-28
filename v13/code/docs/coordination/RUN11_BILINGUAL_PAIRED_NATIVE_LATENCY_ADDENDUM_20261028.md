# Run11 paired bilingual native latency addendum — 2026-10-28

Posthoc descriptive readout from the **same two already frozen, ZIP-hash-verified native artifacts**; no new model runs, no scorer changes, and no performance promotion.

Candidate elapsed per 16 rows: total **288.410 s**, mean **18.026 s**, median **18.487 s**, max **25.371 s**. Baseline: total **180.472 s**, mean **11.280 s**, median **10.731 s**, max **18.918 s**. Candidate was slower on **all 16 paired item IDs**; mean paired delta **+6.746 s**, median paired delta **+7.390 s**, total elapsed ratio **1.598x**. Candidate outputs were **shorter** on average (39.5 vs 72.94 characters), so raw output length alone does not explain the observed elapsed difference. These are one-run Linux wall-time observations, not controlled repeated timings or Redmi latency; runner host/cache/warmup effects and shared-brain state are potential confounds.

This latency tradeoff materially limits the numeric gain interpretation: candidate **12/12** vs baseline **10/12** frozen lexical numeric matches, but a possible **~60% latency cost** on these two runs. A preregistered multi-seed, order-controlled repetition with identical machine/resource profile is needed before selecting the candidate for deployment. Neither native run establishes general semantic utility or any Age promotion.

Input sources: candidate Actions `40637244491` ZIP SHA256 `b64235b1adf9d1cf90139123790c887b4308d7ea6538aafc99fceab690fbc173`; baseline Actions `40637658538` ZIP SHA256 `2efe9bd177f8366626873da452041bd15ffcdc71ee96eb9567fed6d93fdf42ce`; `native/RAW_ROWS.jsonl` elapsed_s per row. The raw artifacts remain in private Library; no raw answers are copied into this report.
