# WP-Z6m BEFUND: §24.17 Deliberation trajectory / halting (real C3/B1/B2)

(Renamed from "Z6i": another thread used WP-Z6i/Z6i2 for route-hint learning the same day.)

Verdict by the preregistered rule: **Z6M_HALTING_PASS** for the simple post-hoc halt readout; trained halt head **not adopted**
(`KEEP_POSTHOC`). Prereg `PREREG.md` (+ amendments A1, A2, written before the test seed ran). Test seed 97, 60 tasks, arms
as listed. Data `v13/bench-results/z6m-halting-20261027/` (`z6m.json` = analysis, `test97_rows.json` = rows, `head.json`).
Training seeds 83/89 (arms d0, d1). The "PASS" is a formal pass of K1-K4 and is read together with the noise band below.

| arm | passed /60 | mean time to answer | mean re-entries |
|---|---|---|---|
| **c3** (C_native only) | **35** | **4.8 s** | 0 |
| d0 (both bodies, no re-entry) | 29 | 27.8 s | 0 |
| d0r (repeat of d0, noise band) | 31 | 28.6 s | 0 |
| d1 (one re-entry) | 32 | 40.4 s | 1 |
| d2 (two re-entries) | 32 | 50.6 s | 2 |
| scaf (shipped scaffold) | 27 | 35.0 s | .67 |
| **posthoc** (continue iff offers disagree) | 33 | 29.7 s | .18 |
| trained halt head | 32 | 28.3 s | 0 |

- K1-K4 pass for posthoc and trained: not dominated by any fixed depth, hard examples not hit harder than easy ones
  (3/25 vs 1/35 lost against d2), quality within 2 of the best fixed depth, cheaper than the deepest. Posthoc continues on 18 % of tasks.
- **K5 FAIL**: the trained head (13 accepted on its held-out set, 11 of 87 training labels were "continue") answered "halt" on all 60
  test tasks, so it behaves exactly like depth 0; it does not beat posthoc (3:4 paired, p = 1.0). `KEEP_POSTHOC`.
- **Noise band**: the identical configuration d0 vs d0r flips 8 of 60 pass/fail outcomes (first offers were byte-identical on only
  28/60 tasks: llama.cpp thread timing). Every paired difference among the body arms (largest 6:3) lies inside that band.
  So depth does not measurably matter on this bench; the formal pass for posthoc says "it is not worse", not "it helps".
- **Main finding (again, as in Z6e/g/h)**: C3 alone is best and about 6× faster. c3 vs d0 8:2 (p = .11), c3 vs posthoc 7:5. The only
  Pareto-optimal arm is c3. A re-entry rescued 8 tasks and broke 5 (d1 vs d0): no net benefit.
- The shipped scaffold (27) is the worst arm, but not significantly (scaf vs d1 2:7, p = .18).

## Consequence
§24.17 is now MEASURED (not only TESTED) for fixed-depth baseline, post-hoc readout, trained head, Pareto view and hard-example check.
Joint/trained halting may not be adopted (does not beat post-hoc). No default changed. A halting head can only matter once
bodies add value over C3 alone (open since Z6e); until then the cheapest correct policy is "do not wake".
Claim limit: generated English tasks, regex checks, bench decoding (threads vary), cloud CPU with 4 shared threads (times are
inflated and not phone times), one test seed, d2 lifts the Age-0 one-cycle cap, only 11 positive labels to train the head.
