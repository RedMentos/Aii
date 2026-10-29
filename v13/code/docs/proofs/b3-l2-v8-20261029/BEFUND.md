# WP-Z4f BEFUND: B3 L2 prefix SHADOW on private/escalate and private/apologize: **L2 FAIL on both tasks**

Prereg `PREREG.md` (commit 7e2926f9, before any real-label number). Single run, data seed 20261301, N = 3000, 5 seeds, 600 test rows per split.
Data `v13/bench-results/b3-l2-v8-20261029/` (report.json, run.log). Checks: runner without prefix = attempt-7 receiver states (max rel. L2 1.3e-7);
L1 adapter read reproduced attempt 7 exactly on every seed; 8-item rerun bit-identical. Runtime 6.6 h, Linux CPU, 4 threads.

Accuracy %, mean of 5 seeds, all channels read through the frozen receiver with the same readout:

| Task | PREFIX_OFF | PREFIX (latent) | SHUFFLED | RANDOM | label word | attr words | EXACT span | L1 adapter read |
|---|---|---|---|---|---|---|---|---|
| escalate | 69.0 | **82.3** | 54.4 | 60.2 | 81.1 | 87.7 | 89.2 | 94.1 |
| apologize | 65.6 | **83.8** | 56.2 | 60.9 | 84.2 | 92.1 | 91.1 | 95.1 |

- Passed: beats prefix off (+13.3 / +18.2 points), shuffled and random controls (content matters, not presence), role retention (drop .0007 / .002),
  calibration (norm ratio 1.001), reproducibility.
- **Failed: utility vs the attribute words (−.056 / −.085), vs EXACT (−.046 / −.050) and vs the label word (+.008 / −.007, not significant).**
  The latent prefix is only as good as a one-word answer and clearly below the two-level-words baseline that the L1 bridge beats.
- L2 is 11-12 points below L1 (82.3 vs 94.1, 83.8 vs 95.1): passing through the frozen backbone loses most of what the L1 adapter read recovers.
- Drift: a topic head trained on prefix-off states falls to 38 % on prefixed states (retrained head: no drop), as in WP-Z4b.

## Consequence
L2 FAIL stays FAIL. B3_LATENT stays at L1_shadow; L3 (tiny residual) locked; LATENT authority 0; runtime unchanged. G-CALLOSUM-UTILITY-002 stays PARTIAL.
Reading: the L1 bridge carries real graded information (replicated), but the frozen receiver backbone does not pass it on through 4 continuous prefix slots.
A new L2 attempt would need a different injection (e.g. trained receiver-side adapter, i.e. L3-like, which is locked by the gate), not a re-tune of this run.
Claim limits: synthetic templates, frozen bodies, one data seed, PCA_ALIGN only, Linux CPU cloud (not Redmi), oracle EXACT span.
