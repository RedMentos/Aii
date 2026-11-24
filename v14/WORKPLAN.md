# V14 active workplan

**Active branch:** `gpt6/v14-m1-isolated-20261124`  
**Historical snapshot:** `backups/V14_PRE_RESET_20261124/v14/`  
**Overall status:** [ENTWURF] — active research and implementation; no release claim.

## Immediate lane: M1 forecasting experiment

The first active implementation lane remains DATA → BASE → PROBE. This is a controlled experiment to establish whether the representation-learning approach learns useful predictive structure beyond simple persistence, raw-window and conventional learned baselines. It is not a substitute for the full distributed V14 architecture.

### Current verified carry-forward

- **DATA:** parser, chronological split, strict missing-value rejection, horizon-aligned seasonal inputs, calendar features, dataset/config/split hashes, hash-gated test access and bounded NumPy batches are present in `v14/m1/`.
- **DATA CI:** synthetic tests passed on Python 3.13 and 3.14 on the previous verified head `8d93236c753f0194224c19edc7411d8d7082b1d6` (GitHub Actions runs 45216218985 and 45216233106). This is synthetic CI evidence, not a real UCI cohort result.
- **BASE:** Persistence, Seasonal Persistence, Train Mean, Train Median, Ridge-AR, LAD/L1-AR and streaming MAE evaluation were present with synthetic tests in the archived snapshot. Raw-Window-Probe (linear MAE readout) and Raw-Window-MLP (one-hidden-layer nonlinear control) have now been added to the clean branch with train-only fitting and synthetic tests; their exact CI result is pending.
- **PROBE:** JEPA encoder/predictor training, direct-MAE control, frozen-representation probe, random-encoder probe and collapse metrics are not yet implemented in this active workspace.
- **Real-data / test year:** no UCI cohort result or test-year evaluation is claimed. The test gate must remain closed until preregistration is fixed and hashed.

The code was selectively copied from the immutable pre-reset snapshot after inspection. Its old copy remains unchanged in the archive.

## Next implementation order

1. Run and inspect the new Raw-Window-Probe/Raw-Window-MLP and paired block-bootstrap tests on Python 3.13 and 3.14. Fix any failures before treating the controls as verified. Check exact input parity, train-only fitting, deterministic seeds, bounded batches and parameter counts.
2. Add the experiment runner and common metric/statistics layer: multi-output horizons 15/30/60, primary average MAE over 15–60, per-horizon/per-channel metrics, paired temporal block bootstrap over days/weeks, same blocks across models and seeds, seed variance reported separately.
3. Implement the direct-MAE model and JEPA representation path with the same data bundle, target horizon, training/validation protocol and probe capacity. Keep Random-Encoder-Probe and raw controls; include effective-rank/collapse telemetry.
4. Complete M1a at T=1 first: backpropagation, baselines, collapse checks, reload/persistence and exact input parity. No test-year access before preregistration hash enforcement.
5. Only after M1a, implement M1b recurrence sweep T=1/2/4 with shared-weight recurrence, unshared compute-matched depth controls and wider parameter/compute controls. Train each condition from scratch with its own seeds.
6. Only after M1b, investigate M1c local learning. Keep activity traces distinct from eligibility traces; derive and test recurrent credit assignment rather than assuming a scalar `lambda e + local` rule is sufficient.

## M1a protocol constraints to preserve

- Retain Ridge-AR and Raw-Window-Probe. Add Persistence, Seasonal Persistence, Train Mean and Train Median; do not replace existing baselines.
- Also retain Raw-Window-MLP, Random-Encoder-Probe, Raw-GRU and direct-MAE control.
- Every primary model receives the same information: L-minute multichannel context X, horizon-aligned historical seasonal values S for every selected channel, and calendar features for each forecast minute. Adapters may differ; information may not.
- UCI target: next 60 minutes, all selected channels; report horizons 15/30/60 and aggregate 15–60.
- Primary optimization/metric for learned probes is L1/MAE. Ridge-AR remains explicitly conventional L2 Ridge; LAD-AR is L1 error with L2 coefficient penalty.
- Raw-Window-Probe is the no-encoder control for the probe itself. Random-Encoder-Probe tests whether learned representation training matters. Direct-MAE tests JEPA against direct target learning.
- Seasonal parity includes Lag-24h and Lag-7d values as input channels, not merely calendar labels. Calendar-only parity is a separately labelled ablation.
- Strict missing-data policy: reject any window missing a required value; no interpolation. Report rejected fractions by split and month.
- Use a fixed maximum candidate L before the pilot. Split gap is fixed from that ceiling, horizon and maximum seasonal lag; do not move split boundaries after seeing validation/test results.
- Split gap must be at least max(max candidate L, H, max seasonal lag) + H.
- Fit/tune only on train/validation. Test access requires exact preregistration SHA-256 plus matching config, split and data fingerprints, with a durable access log written before test windows are exposed.
- Bootstrap overlapping minute windows in paired temporal blocks (days/weeks), not independent windows. Within each replicate compute paired model differences per seed, average over seeds, then CI across replicate averages. Report seed variance separately.
- M1a gate: collapse-free (including effective rank), better than Persistence, Seasonal Persistence and Raw-Window-Probe, and successful persistence/reload. GRU noninferiority is reported but is not a hard M1a gate.

## Status semantics

- [ENTWURF] means protocol or implementation is still being developed.
- [LOCKED] only after the numeric protocol, preregistration file/hash and split manifest are fixed before pilot and enforced by the loader.
- [LOCKED] does not mean implemented, trained or passed.
- Never promote synthetic CI evidence to real UCI, local full-suite, Android or held-out utility evidence.
