# V14 M1 experiment package

**Status:** [ENTWURF] — not preregistered, not locked, no result claimed.

This package starts with the DATA layer. It is deliberately isolated under v14/m1/; it does not replace the V14 master or alter the V13/V14 runtime. The pre-existing development branch was backed up before these files were added.

## DATA implementation

- data.py: UCI minute-file parser, timestamp continuity checks, parameterized windows, chronological split, strict NaN rejection, seasonal lags, future calendar features, split/month rejection statistics, canonical manifest and hashes.
- test_data.py: synthetic logic tests only. These are not a UCI real-data run.
- UCI data is not downloaded by this module. The real-data run must use the user's local extracted UCI file and record its parsed-data fingerprint.

### Split and L handling

The split is defined once using max_candidate_input_length, not recomputed from the currently tested L. The default ceiling is 10,080 minutes (one week); the pilot may vary L only up to that declared ceiling. The default gap is:

max(max_candidate_input_length, H, max(seasonal_lags)) + H

For the standard 7-day seasonal lag and 60-minute target this is 10,140 rows. If the intended pilot includes an L above the declared ceiling, change the ceiling and split *before* the pilot, then preserve the resulting split manifest. Never tune the split against validation/test results.

All input-window, seasonal-lag, calendar and target construction is parameterized by L and H. Missing measurement values cause the complete window to be rejected; no interpolation is performed. Missing or non-contiguous minute timestamps fail closed instead of silently compressing time.

### Test-year protection

build_dataset() materializes only train and validation. It does not return test windows or test metrics.

The only test entry point is load_test_split(). It requires:
- the exact SHA-256 of the preregistration file,
- a matching hash of the complete DataConfig,
- a matching hash of split boundaries,
- a matching fingerprint of parsed dataset rows and channel order.

It appends a test-access event to the specified JSONL log. A hash is a tamper-evident identifier, not a cryptographic authorization system: repository permissions and immutable CI artifacts should protect the preregistration and access log in the actual experiment environment.

## Required DATA acceptance tests

1. UCI parser: semicolon delimiter, decimal comma, missing marker, header/channel order.
2. Timestamp monotonicity and exact one-minute continuity.
3. Fixed split boundaries across all pilot L values up to the preregistered maximum.
4. Split gap and target intervals do not cross split boundaries.
5. Strict NaN rejection across every required input, lag and target channel.
6. Seasonal lag values are horizon-aligned and never from after the forecast origin.
7. Rejection counts and fractions reconcile per split and by month.
8. Manifest and dataset/config/split hashes are deterministic.
9. Test split is unavailable without the exact preregistration hash.
10. Test split rejects config, data or split drift even if the preregistration file itself hashes correctly.

## M1a protocol corrections to preserve

### Status and preregistration

M1a remains [ENTWURF]. [LOCKED] is assigned only after:
- all open numeric values and protocol choices are fixed,
- the split manifest is created before the validation pilot,
- the preregistration document is committed and its SHA-256 recorded,
- the test-year loader enforces that exact hash and matching config/data/split hashes.

Status and evidence remain separate axes. Do not invent additional status labels.

### Fair model input parity

Every primary-comparison model receives the same information bundle:
- X_t: the L-minute multichannel context window,
- S_t: horizon-aligned historical values for every selected channel at the declared seasonal lags,
- calendar features for each forecast minute.

This includes Ridge-AR, Raw-Window-Probe, Raw-Window-MLP, Random-Encoder-Probe, Raw-GRU, direct-MAE control and JEPA. Models may encode/reshape the common bundle differently, but no model may silently omit a feature family or receive extra future information. Seasonal Persistence uses the corresponding lag series.

### JEPA versus direct-MAE objective control

Random-Encoder-Probe only measures the value of learning representations; it does not isolate the value of the JEPA objective.

Add a direct-MAE control with the same encoder/predictor backbone and comparable trainable parameter budget, trained directly against the raw target with MAE/L1 rather than JEPA latent prediction. JEPA is evaluated in its two-stage form: train the JEPA encoder/predictor, freeze the representation, then train a probe. The JEPA probe/readout must have the same capacity, training data, validation tuning budget and selection protocol as the direct-MAE output head. Report the JEPA-to-direct-MAE difference explicitly.

Also include a Raw-Window-MLP probe so a nonlinear model on raw context is represented, not only linear raw probes.

### MAE-aligned optimization

Primary reported metric is MAE, so the primary training objective for learned probes, GRU and direct-MAE control is L1. For the linear autoregressive baseline, report an L1 absolute-error fit with L2 coefficient penalty (label it accurately; it is not ordinary squared-loss Ridge), and retain conventional squared-loss Ridge as a separately named secondary result. Include Train Median alongside Train Mean; the median is the MAE-optimal constant predictor.

### M1b shared-weight recurrence controls

Let the shared recurrent block width be w and recurrence depth be T. A shared block has approximately O(w²) parameters and O(Tw²) compute. Use both matching families:

- **Compute-matched controls:** an unshared depth-T stack with width approximately w, plus a wide T=1 model with width approximately √T · w.
- **Parameter-matched control:** an unshared depth-T stack with width approximately w / √T.

These are initial estimates only. Measure actual trainable parameters and FLOPs from the implemented graph, including input/output projections, normalization, biases and heads; tune widths to the declared matching tolerance. The shared recurrent model demonstrates parameter efficiency only if it beats the parameter-matched unshared stack, or comparable compute with lower memory than the compute-matched controls.

### Seed/block statistics

For each bootstrap replicate, resample the same contiguous temporal blocks for every seed and model. Compute the paired model difference within each seed/block resample, average the paired differences across seeds, and form the confidence interval from those replicate-level averages. Report seed-level effects and seed dispersion separately; never count seeds as independent temporal observations.

### NaN and seasonal coverage reporting

Report candidate, accepted and rejected windows and rejection fraction for each split, plus monthly breakdowns. This is required to reveal seasonal undercoverage after strict NaN rejection and the 7-day lag requirement.

## Not yet implemented

BASE and PROBE model adapters, the validation pilot, preregistration authoring/locking, model training, MAE-vs-JEPA result comparisons, and any UCI real-data run. No gate has passed.