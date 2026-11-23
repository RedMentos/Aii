# WP-Z6g BEFUND: offer number guard

Verdict: **Z6G_NUMBER_GUARD_FAIL** (prereg `PREREG.md`, committed 00dad84 before the run; seed 43, 60 tasks, 5 arms).
Data: `v13/bench-results/z6g-offer-number-guard-20261026/z6g.json`.

| arm | passed /60 | breaks vs C3 alone | rescues | mean time |
|---|---|---|---|---|
| disabled (C3 alone) | **41** | - | - | 2.3 s |
| max (A+B) | 37 | 10 | 6 | 14.3 s |
| max+guard (unknown numbers in body summaries -> [?]) | 37 | 11 | 7 | 14.0 s |
| max+hide (bodies run, C3 sees no hypotheses) | **41** | 4 | 4 | 13.0 s |
| adaptive+guard | 32 | 11 | 2 | 7.4 s |

- G1 max+guard 37 < 41-2. FAIL. G2 11 breaks > 4. FAIL. G3 37 = max 37. FAIL.
- The guard fired (130 hypothesis renders, 13 numbers masked) and changed nothing.

## What it shows
- The hypothesis was wrong: the damage does not come from wrong numbers in the body summaries. Removing the whole
  hypotheses block (max+hide) brings A+B back to exactly the C3-alone level (41); its 4 breaks and 4 rescues are the
  run-to-run noise level. So the *presence* of the internal-hypotheses block in C3's prompt is what costs ~4-10 tasks
  (C3 stops writing out the calculation, answers shorter, follows the hypothesis framing).
- Replicates Z6e on a fresh seed: C3 alone >= every body arm; adaptive wakes and loses.
- Bodies are useful today only through their verified quotes and the observers' detection, not as hypotheses for C3.

## Next
Candidate for the runtime chain (needs a user-visible decision or a prereg with the chain step): render body
hypotheses to C3 only when they carry a source-verified quote or a contradiction the C3 draft lacks; otherwise keep
them for observers/Inquisition. Claim limit: bench hook, generated English tasks, regex checks, one seed, cloud.
