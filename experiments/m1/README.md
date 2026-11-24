# M1 clean-room experiment

Status: implementation draft; no model has been trained on the real UCI dataset.

This workspace is independent of V13/V14 development. It copies selected M1 data/experiment code into a separate package and keeps the previous branches and directories untouched.

## Data contract
- UCI minute-resolution household power data; strict continuity and finite-value validation.
- Production UCI ingestion requires explicit calendar boundaries: validation starts 2008-12-01 00:00; test starts 2009-12-01 00:00.
- The 10,140-row gap is cut from the end of the preceding split, not inserted after the next split begins.
- Candidate origins begin at max_candidate_input_length - 1, not the current L, so candidate denominators remain identical across input-length variants.
- The list and NumPy paths have an elementwise parity test for origins, X, S, calendar features and Y.
- Fraction-based splits remain available only for explicit synthetic/parser fixtures.
- ArrayDataset exposes train rows through train_values(); the full matrix is private internal state. The in-process gate is a methodological API guard, not a security sandbox against code deliberately accessing private attributes. Keep raw data under the ignored `experiments/datasets/` path or outside the repository.
- Test windows require exact data/config/split hashes, complete preregistration fields, and a durable audit event before iteration. The loader resolves the actual Git HEAD itself and refuses a dirty worktree; callers cannot supply a substitute commit hash.

## Modules
- data.py / array_data.py: reference and bounded-memory NumPy data paths, fixed calendar split, gated test access.
- baselines.py: persistence, seasonal persistence, train mean/median, Ridge-AR and LAD-AR.
- raw_probes.py: linear raw-window and nonlinear raw-window MLP controls.
- bootstrap.py: paired temporal-block bootstrap with block-sum/count weighting, including partial blocks. The block-length field is expressed in minute rows; 10,080 minutes (7 days) is only the current default.
- metrics.py: prefix-horizon and primary MAE, per-origin errors, paired multi-model/seed evaluation and atomic result persistence.
- jepa.py: EMA JEPA, Direct-MAE, frozen-context linear probe, random-context probe factory, train-only channel standardization and collapse telemetry.
- dlinear.py: matched-information DLinear control with replicate-edge moving-average decomposition, an explicit future-known S/calendar branch, and a look-back length bound at model construction.
- gru.py: supervised Raw-GRU using the same X/S/calendar information.
- training.py: seeded model construction, training loops, validation telemetry, exact Git HEAD resolution and atomic checkpoints.

## Model contract
- JEPA context encoder sees standardized historical X.
- Predictor sees context latents plus standardized future seasonal S and calendar features.
- EMA target encoder sees standardized future Y only; it is stop-gradient.
- Direct-MAE and Raw-GRU see the same X/S/calendar information and predict raw-unit Y.
- Frozen and random-context probes use the same linear readout and train-only scaler.
- Primary metric is per-origin MAE across all configured channels over forecast steps 15..60; prefix MAE at 15/30/60 is also reported.
- The full design and open choices are in JEPA_DESIGN.md. DLinear is a published baseline control, not a claim that the JEPA model is better; compare all models on identical accepted origins.

## Dependencies
Core tests/data path: numpy. Model training: PyTorch CPU or CUDA.

    python -m pip install -r experiments/m1/requirements.txt
    python -m pip install -r experiments/m1/requirements-ml.txt --index-url https://download.pytorch.org/whl/cpu

## Verification status
- **Current core CI:** 70 tests PASS on Python 3.12, 3.13 and 3.14 at commit `3a118e1ba27f59a10ce52483fbc822d9148781cf` (GitHub Actions run `45331033269`). Includes calendar splits, preregistration gates, NumPy/list parity with missing rows/NaNs, baselines, bootstrap and data integrity.
- **Current torch CI:** 21 tests PASS on Python 3.12, 3.13 and 3.14 at commit `653536e22ea8d5097ed0d94c4e787436eb4bf23d` (run `45330944235`). Includes JEPA, Direct-MAE, Raw-GRU, DLinear, checkpoint and synthetic end-to-end evaluation.
- **LOCAL_PYTHON isolated checks:** DLinear forward/sensitivity/shape-negative/parameter-update checks PASS on Python 3.13.5 + PyTorch 2.10.0+cpu; missing-row list/array origin parity PASS (680/680 synthetic origins). The full repository suite was not run locally because no checkout is mounted in this execution environment.
- No real UCI evaluation has been run in this workspace.
- No test-year windows have been opened.
- No hyperparameter set or preregistration has been locked.

## Next gates
1. Keep the current core and torch CI green on Python 3.12/3.13/3.14 as changes continue.
2. Finish the baseline/statistical review; current synthetic end-to-end training/validation passes, but no real-cohort utility claim is available.
3. Lock patch size/stride, model dimensions, EMA schedule, anti-collapse weights, optimizer, epochs, seeds and promotion thresholds.
4. Run train/validation only on the real UCI data; benchmark ingestion and batch throughput.
5. Hash-lock the preregistration and executing commit before any test access.


## DLinear source and adaptation

The decomposition/linear-forecasting idea follows the DLinear method from Zeng et al., *Are Transformers Effective for Time Series Forecasting?* (AAAI 2023). The official [LTSF-Linear repository](https://github.com/cure-lab/LTSF-Linear) is Apache-2.0 at reviewed revision `0c113668a3b88c4c4ee586b8c5ec3e539c4de5a6`. No upstream source file was copied into this workspace; `dlinear.py` is an independent M1 implementation adapted to the shared future-known X/S/calendar contract. The official model's X-only input is not used unchanged because that would give it less information than the JEPA/Direct-MAE controls.

The original paper's benchmark results are not evidence for this UCI cohort. DLinear must be evaluated here under the same fixed splits, accepted origins, scaler, seeds and paired temporal-block bootstrap as every other model.
