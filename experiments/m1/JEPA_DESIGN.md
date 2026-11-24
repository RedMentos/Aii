# M1a model contract — clean-room design

Status: [BOOT] — model classes and training loops now exist in code; current CI is pending. No real UCI training or test-year access has occurred. This file remains the design contract.

## 1. Task and information boundary

For each origin t:

- Context values: X = x[t-L+1:t+1], shape [B, L, C].
- Known future seasonal covariates: S, shape [B, H, K, C].
- Known future calendar covariates: C_future, shape [B, H, 4].
- Future target values: Y = x[t+1:t+H], shape [B, H, C].

Every deployed predictor receives X, S and C_future. Y is visible only to the training loss or the JEPA target encoder. It must never enter the online context path or predictor inputs.

The first experiment fixes H=60 and reports prefix MAE at 15/30/60 plus the primary mean MAE over steps 15..60, all selected channels.

## 2. JEPA path (T=1)

1. Fit per-channel mean/std on train rows only; apply that scaler to X and S. Patch normalized X along time; project each multichannel patch to d-dimensional tokens.
2. Online context encoder maps X patches to context latents Z_context.
3. Patch known future covariates S and C_future into future query tokens.
4. Predictor cross-attends future queries to Z_context and predicts future latent tokens.
5. EMA target encoder (same architecture/weights initialized from online encoder) maps train-standardized Y patches to target latents Z_target. It is stop-gradient and never receives predictor outputs.
6. Objective is latent prediction error plus a separately logged anti-collapse term. Target-encoder EMA is updated only after the online optimizer step.

The predictor may use all known future queries jointly because S and calendar values are known at the forecast origin. No future target values are available to it.

## 3. Matched controls

- Direct-MAE: same context encoder and future-query predictor geometry; apply the train-only input scaler to X/S, replace latent prediction head with a value-space head and train with raw-unit L1/MAE on Y. No EMA target encoder.
- Frozen JEPA probe: freeze the JEPA-trained online context encoder; train only a shared linear readout on its final context token plus standardized S, calendar and fixed horizon-position features.
- Random-encoder probe: same probe and same frozen encoder architecture, but use an untrained seeded encoder.
- Raw-Window-Probe: linear L1 readout over the flattened X/S/calendar bundle.
- Raw-Window-MLP: one-hidden-layer nonlinear raw-input control.
- Matched DLinear: replicate-edge moving-average decomposition of X into trend/residual, independent per-channel time-linear heads, plus a per-horizon projection of known future S/calendar. This M1 adaptation retains the common information contract; it is not an exact reproduction of the original X-only DLinear benchmark.
- Raw-GRU: supervised recurrent model with the same X/S/calendar information.
- Conventional baselines: Persistence, Seasonal Persistence, Train Mean/Median, Ridge-AR and LAD-AR. Ridge-AR remains explicitly a secondary conventional baseline if its sparse lag adapter is retained.

Trainable parameter counts, total parameter counts, FLOPs/steps, and training examples must be reported separately. An EMA target encoder is not a second independently trained model.

## 4. Collapse telemetry

At minimum, record for context and target embeddings:
- mean per-dimension standard deviation (stdZ);
- covariance spectrum;
- effective rank from normalized singular values;
- minimum/median/maximum dimension standard deviation;
- latent prediction loss and each anti-collapse component separately.

Do not infer collapse-free behavior from a finite loss alone. A collapse gate needs declared thresholds fixed before validation tuning.

## 5. Split, optimization and evaluation

- Fixed calendar split and 10,140-row gap are defined in data.py.
- Fit channel scaling and model weights only on train. Select hyperparameters/checkpoints on validation. The scaler is serialized with the checkpoint and may not be fitted on validation or test.
- Compare all models on identical accepted forecast origins.
- Bootstrap paired per-origin primary MAE by non-overlapping temporal blocks; use the same sampled blocks for every model and seed. The preregistered bootstrap_block_len is in minute rows; current default is 10,080 (7 days), anchored to the first accepted origin. Aggregate block sums/counts so short edge blocks do not receive the same weight as full blocks.
- Report seed variance separately from temporal uncertainty.
- Test-year access remains gated by exact config/split/data hashes, complete preregistration and exact executing commit SHA, plus a durable access event.

## 6. Implementation choices to lock before training

- Patch length and stride.
- Latent width, encoder depth/heads and predictor depth/heads.
- Target EMA schedule and update timing.
- Exact anti-collapse objective and coefficients.
- Direct-MAE decoder capacity and parameter-matching rule.
- Probe readout capacity.
- Bootstrap block length in minute rows.
- Optimizer, schedule, epochs, batch size, seeds and training-step budget.
- Numeric collapse thresholds and M1a promotion criteria.

No test-year results may be used to choose any of these values.

## 7. External implementation review

- TimeJEPA (MIT) is a relevant time-series JEPA reference for context/target encoders, EMA target updates, future-query prediction and a separate forecasting head. This workspace uses its architecture as a design reference only; no TimeJEPA source code has been copied. Its current repository describes itself as a time-series JEPA forecaster; its paper is listed as in preparation.
  - https://github.com/IUseAMouse/TimeJEPA
- Sennadir/TS_JEPA is another time-series JEPA implementation. The repository metadata reports no declared license, so no source code is copied or adapted from it.
  - https://github.com/Sennadir/TS_JEPA

The M1 design above is adapted to this dataset's X/S/calendar information contract rather than reproducing either external project.


## 8. DLinear control and source boundary

The DLinear control is based on the decomposition-linear method in Zeng et al., *Are Transformers Effective for Time Series Forecasting?* (AAAI 2023; arXiv:2205.13504). The official implementation is `cure-lab/LTSF-Linear`, Apache-2.0, reviewed at commit `0c113668a3b88c4c4ee586b8c5ec3e539c4de5a6`. No upstream code was copied; the M1 module independently implements replicate-edge moving-average decomposition and time-axis linear heads.

The original DLinear implementation consumes historical X only. M1 adds a separate linear projection over known future seasonal covariates and calendar features so DLinear, Direct-MAE, Raw-GRU and JEPA receive the same permitted information. This changes the model from an exact reproduction into a matched-information adaptation. Results from the original nine-dataset benchmark do not establish performance on this UCI cohort.
