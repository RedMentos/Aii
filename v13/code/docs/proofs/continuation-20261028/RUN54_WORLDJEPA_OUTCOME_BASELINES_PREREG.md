# Run54 — Synthetic digital action/outcome baseline comparison (2026-10-28)

Owner GPT-6 continuation. Independent new-file child of Run52 PR #960 exact parent `c13169bd1305489e57fc313a645f5c898af1ea12`, conditional on Run52 source-only GREEN. Disjoint file ownership from Run53 permutation provenance: Run54 adds only `v13/code/v13/world_jepa_synthetic_outcome_baselines.py`, its tests, prereg and CI. No modification of WorldJEPA, Run50/51 sources, Store/Runtime or registered models/seeds.

## Motivation
Canon §7.2.1 requires distinct forward, inverse, state-alignment and outcome evidence. Run51 has a synthetic action-conditioned latent diagnostic but not a calibrated outcome baseline. A synthetic fixture with outcome explicitly depending on action can produce apparently good latent metrics even if the task is trivial to solve with a linear action predictor. Before attributing any utility to JEPA, quantify this simpler explanation and retain per-outcome metrics.

## Fixed experiment
Only the exact Run50 `FakeReadOnlyView(128)` synthetic fixture accepted by Run51's immutable source/array digests is eligible. Explicit `approved_shadow_fit=True`, `source_kind='SYNTHETIC_TEST_ONLY'` must pass Run51 validation before any readout. Copy inputs before fitting, no Store, Runtime, file writes or model publication. Fit Run51 observed/shuffled WorldJEPA as already authorized, and compare four **training-only** regularized linear readouts predicting original outcome `y3=X2[:,4:]` on the disjoint heldout rows: intercept/mean, state4, state4+true route onehot4, state4+independently shuffled train routes (holdout true route). Ridge lambda fixed 0.01, intercept unregularized. Report overall and per-target heldout MSE (log_duration, success, log_chars), baseline shuffle SHA256 and Run51 latent aggregate metrics. Do not train on holdout or use heldout labels for selection.

Exploratory local arithmetic reconstruction before prereg, NOT V13-native proof: n_train=89, holdout=39, ridge lambda .01; state-only overall MSE ~0.001031, state+route ~0.0000913, shuffled-route ~0.001021. Action effect is injected into synthetic duration by fixture design; no real causal identification or V13 learning gain follows. These numbers are not frozen acceptance thresholds and must be independently measured by CI.

## Acceptance
Deterministic bounded synthetic-only execution, no input mutation, explicit refusal for missing approval, real source, changed manifest/arrays; per-target metrics finite and source-pinned. In synthetic fixture action-conditioned linear duration prediction should outperform shuffled control, proving only fixture signal. Compare WorldJEPA's observed/shuffled latent diagnostics descriptively; no claim of advantage over linear ridge without actual measurements. Preserve Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi UNMEASURED, full V13 incomplete.

CI: pinned NumPy and focused/full Linux software, original WorldModel/WorldJEPA/Run50/Run51 source SHA pins, privacy/diff and raw artifact SHA256SUMS. Exact-head raw independent audit required before GREEN.
