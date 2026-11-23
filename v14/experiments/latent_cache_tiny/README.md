# Tiny cross-geometry KV-cache adapter experiment

**Evidence label:** `LOCAL_LINUX_TINY_MODEL_PROOF_NOT_PRODUCT_NATIVE`.

This experiment trains two small decoder-only models with different cache geometries, learns a directed sender-to-receiver K/V adapter, injects the transformed cache into the receiver, and compares against exact-context, no-message, shuffled-cache and random-adapter controls. It has two adapter phases: receiver-cache reconstruction, then receiver task-loss supervision.

It is a mechanism proof, not a V13 production adapter. The models are newly initialized toy PyTorch decoders and the task is synthetic associative recall. It does not use LFM2.5, Qwen3.5, llama.cpp, GGUF, production user data, a real B1/B2 Runtime consumer, OOD tasks, a symbolic-message baseline, or Android hardware.

## Run

Requires Python 3.13, NumPy 2.3.5 and CPU PyTorch 2.10.0.

```bash
python -m pip install numpy==2.3.5
python -m pip install torch==2.10.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu
python -m py_compile latent_cache_tiny.py test_latent_cache_tiny.py
python -m unittest -v
python latent_cache_tiny.py
```

The CI job pins these test-only dependencies and runs the experiment's tests explicitly; the generic experiment-directory discovery does not recurse into this folder. PyTorch and NumPy are BSD-3-Clause test dependencies only; neither is added to the product/runtime dependency set, and no model weights or data are downloaded.

## Exact local result

Sender: 2 layers × width 24 × 4 heads. Receiver: 3 layers × width 32 × 4 heads. Both models trained for 320 steps; adapter Phase I ran 360 reconstruction steps and Phase II ran 180 generation-supervision steps.

| Metric, seed 13 | Result |
| --- | ---: |
| Held-out cache reconstruction MSE | 6.5134 → 0.2054 |
| Latent accuracy after Phase I | 85.94% |
| Final latent receiver accuracy | 100.00% |
| Exact receiver-context accuracy | 100.00% |
| No-message accuracy | 0.00% |
| Shuffled-cache accuracy | 12.50% |
| Random-adapter accuracy | 13.28% |
| Adapter parameter Δ L2 | 20.2719 |
| Peak Phase-I gradient norm | 2.1451 |
| Restart max absolute logit delta | 0.0 |

Three additional seeds (17, 29, 41) also produced 100% held-out latent accuracy. Shuffled-cache accuracy was 13.28%, 7.03%, and 13.28%; random-adapter accuracy was 9.38%, 11.72%, and 17.97%. Held-out reconstruction MSE fell from 6.7926→0.2041, 6.4253→0.2405, and 5.9977→0.2062 respectively. These are repeated runs on the same synthetic task family, not OOD generalization.

The seed-13 experiment took 12.41 s wall time and peaked at 344,584 KiB RSS on the available local Linux CPU. The three focused unit tests passed in 9.9 s. `py_compile` passed.

## What this establishes and what it does not

It establishes that a trained directed adapter can map actual numeric K/V tensors across different tiny layer counts and hidden widths, that the receiver can use the mapped cache to solve a task without receiving the source tokens, and that the update survives serialization/reload exactly in this toy setting.

It does **not** establish that the same mapping works for LFM2.5 ↔ Qwen3.5, that the production llama.cpp runner can tap or inject native caches, that B3 is useful or calibrated, that the method is robust OOD, or that the Android memory/latency budget is acceptable. Production `LlamaRunner` still reports `CAN_LATENT_TAP=False`, `CAN_LATENT_INJECT=False`, and `CAN_TRAIN_BODY=False`; a real native adapter requires a model-specific tap/injection path and real-model causal controls.
