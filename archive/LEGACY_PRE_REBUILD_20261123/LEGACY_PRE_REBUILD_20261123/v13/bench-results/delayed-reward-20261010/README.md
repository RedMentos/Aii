# §99 delayed reward + WP-T12 per-sample δ (2026-10-10)

`code/v13/ablation99.py` `delayed_ablation` (test `test_ablation99.py::DelayedReward`), real `Neuromod`, 5 seeds. Four control paths are touched in bursts of 5 with 20–60-event gaps. The outcome of each touch arrives 3–40 events later. 70 % of samples carry the true label, 30 % a biased label. The outcome report itself is wrong 10 % of the time. The learner updates a sample when its outcome arrives, scaled by the arm's factor at that moment.

| Arm | final error (mean ± sd) | good/bad factor |
|---|---|---|
| **v13 + δ per sample** (WP-T12 `local_update`, sign of r − r̂) | **.051 ± .019** | **12.8** |
| v13 gate (fast + slow trace) | .158 ± .045 | 1.11 |
| fast trace only | .159 | 1.11 |
| slow trace only | .160 | 1.11 |
| recency only | .176 | 1.05 |
| gradient only, budget matched | .182 | 1.00 |
| random mask | .224 | 1.08 |
| gradient only | .242 | 1.00 |
| oracle (true good flag) | .003 | – |

- **v13 + δ** beats every other arm in 5 of 5 seeds, except the oracle.
- **v13 gate alone** beats recency-only and budget-matched gradient 5 of 5, and fast-only and slow-only only 2 of 5.

**Results.**
1. **The second (slow) eligibility timescale adds nothing measurable:** v13 and fast-only are the same.
2. **The gate alone cannot assign credit per sample:** its modulator is per path, so it separates confirmed from unconfirmed samples by only 1.1×.
3. **The fix is the §12.4 local error δ per sample** (WP-T12). The signed reward-prediction error r − r̂ against the path's expected outcome gates which samples are imitated. This triples accuracy (.158 → .051) despite 10 % wrong outcome reports, and separates confirmed from unconfirmed samples 12.8×.

The remaining gap to the oracle comes from the 10 % wrong outcome reports and the gate budget. With binary outcomes the sign of δ equals the confirmation; r̂ only matters for graded outcomes.

**Claim limit:** synthetic open-loop stream, linear NLMS learners, no language model.
