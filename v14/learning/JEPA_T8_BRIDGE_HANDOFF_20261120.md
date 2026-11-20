# V14 temporal outcome semantics integration handoff — 2026-11-20

**Owner:** Boss & Integration. **Work item:** V14-004 / V14-007.
**Branch:** `boss/v14-temporal-outcome-semantics-20261120`. **Base:** `14d7386484dfce6728aa404d89eae98403b4dba0`. **Status:** candidate only; not merged or released.

## Functional change

The temporal outcome substrate now distinguishes:
- `OBSERVED`: expected outcome inside the time window; error = `1-p`.
- `MISMATCHED`: a different outcome was actually observed; error = `-p`.
- `EARLY` / `DELAYED`: expected outcome outside the predicted window; error = `-p`.
- `OMITTED`: the observation window completed with source-bound evidence and no event; error = `-p`.
- `CENSORED` / `CANCELLED`: no learning signal.

Previously, any `observed=True` was scored positively and the expected `outcome` label was not compared. That incorrectly rewarded late or wrong outcomes. The receiver now checks explicit expected/observed labels, exact boolean permissions, finite numeric values, bounded identifiers, and persistent rollback/restart behavior.

## Local evidence

Environment: **LOCAL_LINUX**, Python 3.13.5, x86_64.
Commands:
- `python -m py_compile temporal_outcomes.py temporal_receiver.py t8_temporal_bridge.py`
- `python -m unittest -v test_temporal_outcomes test_temporal_receiver test_t8_temporal_bridge`

Result: **18/18 tests PASS**. These are the exact source/test files assembled from the GitHub candidate plus this correction, executed as an isolated package. This is not a full repository test run and not a native/Android test.

SHA-256:
- `temporal_outcomes.py`: `a53d3dca9aa97f43620997f17081b5553b6b1b25483473fb824b01591013eef1`
- `temporal_receiver.py`: `9bb6be6815bf48c548b8d441a2d445ba33b5577a4231edf6a24141f4a4b33316`
- `t8_temporal_bridge.py`: `37e413dcf5576c9b024c4c81c7de6b88ffcfb6d420c649de08b81ddf77cd674e`
- `test_temporal_outcomes.py`: `094dc6ab2909f660d6407e9892973870c79230d7ef31b8173770fc4581e09be3`
- `test_temporal_receiver.py`: `175826ea4d9cad38e9a215f6a103d5b1295d07dec978df6a845578fc6b1c31b2`
- `test_t8_temporal_bridge.py`: `f1d1fadf52526043a39e6c1beb76928e68fffde23ae4a8b9cd483bf13327f975`

## Explicit limitations

- The receiver is a tiny persistent scalar readout, not a JEPA encoder, native B1/B2 model adapter, GGUF optimizer, or full model-weight update.
- `trusted=True` remains a caller-supplied contract. It is **not authentication**; this bridge is not safe for live producer integration until a Store/World-bound authenticated T8 envelope replaces it.
- No runtime consumer, actual T8 producer, held-out utility/retention experiment, Termux test, or Redmi receipt exists for this branch.
- No model, model weights, permissions, Age, updater, or phone state was changed.

## Next executable gate

Implement a producer that reads and verifies the actual persisted Store/World T8 action/transition records, binds event identity and source hashes, and issues a non-forgeable in-process capability to the temporal bridge. Then connect it to the real runtime learning consumer and test holdout utility, retention, checkpoint/restart, rollback, and negative controls. Until then V14-004 remains **IN_PROGRESS_PARTIAL**, not complete.