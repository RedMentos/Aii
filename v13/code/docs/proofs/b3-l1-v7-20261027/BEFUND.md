# B3 L1 attempt 7 (WP-Z4e) BEFUND, data seed 20261301: canon L1 PASS on private/escalate AND private/apologize

Prereg `PREREG.md` (commit c4da9d3 before any state was computed; amendment A1 after an OOM kill with no results seen).
Recipe of attempt 5 unchanged, N = 3000 rows (600 test rows per split), 5 split seeds, new B1/B2 states.
Data `v13/bench-results/b3-l1-v7-20261027/seed20261301/` (report, bridges; states stay on the cloud machine).

Private view, accuracy %, mean of 5 split seeds:

| Task | NO_MSG | EXACT | label word | attr words | SCALAR | **LATENT** | LATENT − attr words (utility) | canon | strict (vs SCALAR) |
|---|---|---|---|---|---|---|---|---|---|
| escalate | 69.0 | 82.3 | 80.7 | 87.2 | 93.6 | **94.1** | +.068 ± .007, 5/5 | **PASS** | FAIL (+.001 ± .007, 3/5) |
| apologize | 65.6 | 88.3 | 83.9 | 92.2 | 95.1 | **95.1** | +.026 ± .004, 5/5 | **PASS** | FAIL (−.004 ± .008, 2/5) |

All other gate criteria hold on both tasks: beats NO_MESSAGE, shuffled and random controls, CONTROL, EXACT, label word (+.13 / +.11)
and attribute words, role retention drop 0, receiver OOD ≈ 1 %, reload identical. Shuffled/random LATENT fall to 52-64 %.

## What it shows
- Power was the limit (attempt 6 hypothesis confirmed): at 5× the test rows the 1-4 point edge of attempts 5/6 is a clear
  +2.6 to +6.8 point edge over the best symbolic baseline with 5/5 split wins.
- LATENT is statistically *equal* to the 2 × fp16 privileged-estimate SCALAR (strict gate FAIL, difference −.4 to +.1 points): the
  bridge recovers about all the information a two-number message would carry, not more. The canon rule (words) is passed; the
  strict rule is not.
- The earlier apologize "never passed" and the seed-dependence were small-sample effects; this is still ONE data seed.

## Consequence (preregistered)
Per PREREG: a PASS on one seed re-opens the L2 prefix SHADOW experiment only after replication on a second fresh 3000-row seed
(20261302, run next). LATENT authority stays 0, runtime unchanged, G-CALLOSUM-UTILITY-002 stays PARTIAL (needs 8 axes, L2-L4).
Claim limits as attempt 5: L1 receiver-adapter read only (no backbone injection), synthetic templates, aux targets are privileged
labels, oracle EXACT span, Linux CPU, not Redmi.

## Replication, data seed 20261302 (preregistered, 0 shared sender texts with all earlier seeds): REPLICATED
Private view, accuracy %, mean of 5 split seeds:

| Task | NO_MSG | label word | attr words | SCALAR | **LATENT** | canon | strict (vs SCALAR) |
|---|---|---|---|---|---|---|---|
| escalate | 68.3 | 80.8 | 89.7 | 93.6 | **93.9** | **PASS** | FAIL |
| apologize | 64.6 | 84.5 | 92.2 | 96.6 | **94.3** | **PASS** | FAIL |

Rule of PREREG A2 (canon PASS on the same task on the second seed) is met for both tasks: **REPLICATED**. First replicated L1 pass in the
B3 series after attempts 3-6 (power was the limit). Strict rule vs SCALAR still FAIL on both seeds (apologize SCALAR is ahead by 2.3 here).
Consequence: L2 prefix SHADOW on private/escalate and private/apologize may be reopened with a NEW prereg. LATENT authority stays 0,
runtime unchanged, G-CALLOSUM-UTILITY-002 stays PARTIAL. Same claim limits as above.
