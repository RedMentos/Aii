# Run116 — LateWatch completed-tail number must be checked at stream finish (preregistered)

2026-10-25 UTC. Parent: verified Run114 PR #145 `6fce98c2111429b1951e6e527608cb9c543c21b3`. Owner: `v13/code/v13/latewatch.py`, new Run116 tests/workflow/evidence only. Existing `test_latewatch.py` is read-only regression. No edits to Runtime, Body models, Context OS, episodes.py (Run106 active owner), World Model, canonical blueprint, native cohorts or approval gates.

## Repro hypothesis
`complete(partial)` intentionally drops a numeric suffix while a C3 stream is still growing, to avoid a false interrupt on partial numbers. `Watcher.finish` reuses `disagreement(offer, output, source)` on the **completed** output, so it also drops a now-complete final number. Example: source asks `46 + 62`, late B1 says `108`, final C3 text ends `... answer is 100`. The current code may miss the contradiction and label it AFTER_OUTPUT with no reason. This is an inference from current source; require test-first RED before claiming it.

## Locked behavior
- Streaming checks retain the existing partial-number suppression and all thresholds; no earlier interruption or authority expansion.
- Only the post-stream `finish` comparison may treat the terminal number as complete.
- Completed correct numeric answers do not generate a conflict; source numbers alone are not a conflict.
- Late offer remains subject to existing gated `selfmodel.late_offer` pathway; no automatic correction, new external effectors or new Age permissions.
- Test pure final-vs-partial distinction, Watcher.finish status/reason and inherited LateWatch tests. Preserve RED/GREEN logs and privacy scan.
- No STEP2/B3/Body-JEPA/DS2/whole-system gate promotion.

## Evidence class
Linux software/synthetic mock only; not native model or Redmi. Next: independent review of actual stream-boundary behavior and source refs on real device.
