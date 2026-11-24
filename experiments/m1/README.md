# M1 clean-room experiment

Status: implementation draft; no model has been trained on the real UCI dataset.

This is a standalone, clean-room forecasting experiment under `experiments/m1/`. It does not modify the installed Android runtime, model files, permissions or device state.

## Data contract
- UCI minute-resolution household power data; strict continuity and finite-value validation.
- Production UCI ingestion requires explicit calendar boundaries: validation starts 2008-12-01 00:00; test starts 2009-12-01 00:00.
- The 10,140-row gap is cut from the end of the preceding split, not inserted after the next split begins.
- Candidate origins begin at max_candidate_input_length - 1, not the current L, so candidate denominators remain identical across input-length variants.
- The list and NumPy paths have an elementwise parity test for origins, X, S, calendar features and Y.
- Fraction-based splits remain available only for explicit synthetic/parser fixtures.
- ArrayDataset exposes train rows through train_values(); the full matrix is private internal state. The in-process gate is a methodological API guard, not a security sandbox against code deliberately accessing private attributes. Keep raw data under the ignored `experiments/datasets/` path or outside the repository.
- Test windows require exact data/config/split hashes, complete preregistration fields, and a durable audit event before iteration. The loader resolves the actual Git HEAD itself and refuses a dirty worktree; callers cannot supply a substitute commit hash.

## Dataset provenance

The intended real cohort is UCI's *Individual Household Electric Power Consumption* dataset, DOI [10.24432/C58K54](https://doi.org/10.24432/C58K54), by Georges Hebrail and Alice Berard. UCI lists 2,075,259 minute-level measurements from one household in Sceaux, France, spanning December 2006 through November 2010, with nearly 1.25% missing measurement rows. The raw file is `household_power_consumption.txt`; UCI lists the dataset under **CC BY 4.0**. Keep the downloaded file local under the ignored `experiments/datasets/` path; never commit it. This is a single-household case study, not evidence of population-level generalization.

No real UCI file was available in this execution environment: the Library search did not surface it, and the runtime could not materialize the UCI archive. Therefore all current model results remain synthetic/software checks; real train/validation utility is still unmeasured and the test year remains locked.

## Modules
- data.py / array_data.py: reference and bounded-memory NumPy data paths, fixed calendar split, gated test access.
- baselines.py: persistence, seasonal persistence, train mean/median, Ridge-AR and LAD-AR.
- raw_probes.py: linear raw-window and nonlinear raw-window MLP controls.
- bootstrap.py: paired temporal-block bootstrap with block-sum/count weighting, including partial blocks. The block-length field is expressed in minute rows; 10,080 minutes (7 days) is only the current default.
- metrics.py: prefix-horizon and primary MAE, per-origin errors, paired multi-model/seed evaluation and atomic result persistence.
- jepa.py: EMA JEPA, Direct-MAE, frozen-context linear probe, random-context probe factory, train-only channel standardization and collapse telemetry.
- dlinear.py: matched-information DLinear and NLinear controls; DLinear uses replicate-edge trend/residual decomposition, while NLinear centers X on its last value. Both include a future-known S/calendar branch and bind look-back length at construction.
- gru.py: supervised Raw-GRU using the same X/S/calendar information.
- training.py: seeded model construction, training loops, validation telemetry, exact Git HEAD resolution and atomic checkpoints.
- runner.py: validation-only multi-model pilot; applies a per-epoch train-window cap only to fitting, evaluates every model on the full shared validation origins, saves model checkpoints and writes one provenance-bound result JSON. JEPA pretraining is recorded separately from raw-unit forecast predictors.
- download_uci.py: explicit official-host-only dataset downloader; checks ZIP CRC, path traversal, archive/member sizes and overwrite policy, then writes a SHA-256 provenance sidecar. It is never invoked automatically by the runner.

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



## Validation-only runner

The runner turns the model modules into one repeatable experiment. It does not download data automatically and never opens the test year.

1. Explicitly download the official UCI archive. The downloader only accepts HTTPS on `archive.ics.uci.edu`, verifies the ZIP and extracts only the expected data member:

```bash
python -m experiments.m1.download_uci --output-dir experiments/datasets
```

2. Keep the raw file and its generated `.provenance.json` sidecar under the ignored `experiments/datasets/` directory; never commit either. Existing files are not overwritten unless `--force` is explicitly supplied.
3. Run from a clean Git checkout so the runner can record the exact executing HEAD:

```bash
python -m experiments.m1.runner \
  --data experiments/datasets/household_power_consumption.txt \
  --output experiments/results/m1-validation-pilot.json
```

The default is an **exploratory pilot**, not a locked experiment: one seed, one epoch, and at most 4,096 accepted training windows per epoch for models that learn weights. Neural channel scalers use all raw train rows; raw-window and AR feature scalers use all accepted train windows; the cap limits optimizer/linear-fit windows only. Train Mean/Median use all accepted train target timestamps. Every forecast model is evaluated on the full validation split and identical accepted origins. Increase seeds, epochs and the training-window cap through a JSON `PilotConfig` override only after reviewing the compute budget.

The runner writes the canonical result JSON and a separate `*.checkpoints/` directory beside it. It refuses to overwrite an existing result or checkpoint directory. The result records the raw-file and parsed-data hashes, split statistics, code SHA, model parameter counts, training histories, checkpoint hashes, per-origin paired block-bootstrap intervals and the explicit `test_split_accessed=false` gate.

JEPA is a latent pretraining objective, not a raw-unit forecast head. Its latent loss and collapse telemetry are recorded separately; forecast MAE is measured through the trained frozen-context probe, Direct-MAE, DLinear/NLinear, Raw-GRU and the other raw/baseline controls. Do not rank the JEPA latent loss against forecast MAE.

## Verification status
- **Core CI:** 70 tests PASS on Python 3.12, 3.13 and 3.14 at latest documentation-aligned HEAD `97d653753204a97cedf9fbf6d9610ada78dd9af0` (run [45383562209](https://github.com/RedMentos/Aii/actions/runs/45383562209)). Includes the NumPy data path, fixed splits, preregistration gates, baselines, paired bootstrap, metrics and integrity checks.
- **Torch/runner CI:** 27 tests PASS on Python 3.12, 3.13 and 3.14 at code commit `85ec5707db0c5f11c69370d5c44ef88bb9f1dd7b` (run [45383148140](https://github.com/RedMentos/Aii/actions/runs/45383148140)). Includes the full synthetic runner across all model families, checkpoint writes, same-origin validation, JEPA-pretrain separation, DLinear/NLinear, Raw-GRU and existing JEPA regressions. Later commits changed only README/design documentation.
- **Earlier runner regression:** the first runner CI exposed that JEPA latent pretraining was incorrectly sent through a raw forecast adapter. The failed run [45382620774](https://github.com/RedMentos/Aii/actions/runs/45382620774) was corrected by treating JEPA as a training/telemetry dependency and evaluating its frozen-context probe for raw-unit MAE. The exact updated runner passed in run 45383148140.
- **LOCAL_PYTHON:** isolated train-window-cap helper smoke PASS on Python 3.13.5 / NumPy 2.3.5 (37 training windows capped as 16+16+5; validation remained uncapped at 23 windows). The full repository suite was not run locally because no checkout is mounted in this execution environment.
- **Real UCI train/validation:** NOT_RUN. The raw file is not present in the local runtime or Library; the attempted official archive download did not complete.
- **Test-year access:** LOCKED; no test windows have been opened.
- **Hyperparameters/preregistration:** NOT_LOCKED. The runner defaults are explicitly exploratory and are not promotion evidence.

## Next gates
1. Obtain the official UCI file locally, verify its raw SHA-256, and run the validation-only pilot on the real train/validation cohort.
2. Inspect accepted/rejected windows by month, missingness, full-validation baseline metrics, paired temporal-block intervals and per-seed variance before changing the model contract.
3. Benchmark ingestion, fit time, peak RSS and evaluation throughput on the real file; adjust the exploratory cap/batch sizes without touching test-year data.
4. Only after reviewing pilot evidence, lock architecture/optimizer/EMA/anti-collapse settings, seeds and numeric promotion criteria in a separate preregistration.
5. Open test windows only through the existing exact hash/clean-HEAD preregistration gate and durable audit event.

## DLinear source and adaptation

The DLinear and NLinear ideas follow Zeng et al., *Are Transformers Effective for Time Series Forecasting?* (AAAI 2023). The official [LTSF-Linear repository](https://github.com/cure-lab/LTSF-Linear) is Apache-2.0 at reviewed revision `0c113668a3b88c4c4ee586b8c5ec3e539c4de5a6`. No upstream source file was copied into this workspace; `dlinear.py` is an independent M1 implementation adapted to the shared future-known X/S/calendar contract. The official model's X-only input is not used unchanged because that would give it less information than the JEPA/Direct-MAE controls.

The original paper's benchmark results are not evidence for this UCI cohort. DLinear must be evaluated here under the same fixed splits, accepted origins, scaler, seeds and paired temporal-block bootstrap as every other model.
