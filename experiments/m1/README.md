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
- ArrayDataset exposes train rows through train_values(); the full matrix is private internal state. The in-process gate is a methodological API guard, not a security sandbox against code deliberately accessing private attributes.
- Test windows require exact data/config/split hashes, complete preregistration fields, exact executing commit SHA, and a durable audit event before iteration.

## Modules
- data.py / array_data.py: reference and bounded-memory NumPy data paths, fixed calendar split, gated test access.
- baselines.py: persistence, seasonal persistence, train mean/median, Ridge-AR and LAD-AR.
- raw_probes.py: linear raw-window and nonlinear raw-window MLP controls.
- bootstrap.py: paired temporal-block bootstrap with block-sum/count weighting, including partial blocks. The block-length field is expressed in minute rows; 10,080 minutes (7 days) is only the current default.
- metrics.py: prefix-horizon and primary MAE, per-origin errors, paired multi-model/seed evaluation and atomic result persistence.
- jepa.py: EMA JEPA, Direct-MAE, frozen-context linear probe, random-context probe factory, train-only channel standardization and collapse telemetry.
- gru.py: supervised Raw-GRU using the same X/S/calendar information.
- training.py: seeded model construction, training loops, validation telemetry, exact Git HEAD resolution and atomic checkpoints.

## Model contract
- JEPA context encoder sees standardized historical X.
- Predictor sees context latents plus standardized future seasonal S and calendar features.
- EMA target encoder sees standardized future Y only; it is stop-gradient.
- Direct-MAE and Raw-GRU see the same X/S/calendar information and predict raw-unit Y.
- Frozen and random-context probes use the same linear readout and train-only scaler.
- Primary metric is per-origin MAE across all configured channels over forecast steps 15..60; prefix MAE at 15/30/60 is also reported.
- The full design and open choices are in JEPA_DESIGN.md.

## Dependencies
Core tests/data path: numpy. Model training: PyTorch CPU or CUDA.

    python -m pip install -r experiments/m1/requirements.txt
    python -m pip install -r experiments/m1/requirements-ml.txt --index-url https://download.pytorch.org/whl/cpu

## Verification status
- Earlier core suite: 62 synthetic tests passed on Python 3.12, 3.13 and 3.14 at commit 016239ff53b5de227b8b987cf1f39873a975f252 (historical; subsequent calendar/loader changes are awaiting the latest CI run).
- Earlier torch suite: passed on Python 3.12/3.13/3.14 before the later scaler/probe changes; current torch suite is awaiting CI.
- No real UCI evaluation has been run in this workspace.
- No test-year windows have been opened.
- No hyperparameter set or preregistration has been locked.

## Next gates
1. Get the current core and torch CI green on Python 3.12/3.13/3.14.
2. Finish the baseline/statistical review and confirm the synthetic end-to-end training/validation test passes.
3. Lock patch size/stride, model dimensions, EMA schedule, anti-collapse weights, optimizer, epochs, seeds and promotion thresholds.
4. Run train/validation only on the real UCI data; benchmark ingestion and batch throughput.
5. Hash-lock the preregistration and executing commit before any test access.
