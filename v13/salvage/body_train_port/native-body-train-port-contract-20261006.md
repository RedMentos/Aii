# Native body train-port contract — 2026-10-06

Implemented a fail-closed binding contract for the canon-required future native B1/B2 training port.

What is proven by source/tests: an explicit descriptor must bind the exact inference model, a distinct fp32/fp16/bf16 master artifact, an executable native train runner, an executable requantizer, hashes for every artifact, and a finite explicit trainable-parameter ID set. Tampering, quantized/inference-as-master, missing artifacts, non-executable tools, wrong role/schema and unsupported dtype fail closed. A fully bound descriptor still has `update_authority=0` and remains `UNAVAILABLE` until a real TrainRunnerProof demonstrates gradients/EMA/requantization/retention on the exact revision.

What is NOT proven: no native body training occurred; no master weights are shipped; no sparse body exists; no JEPA objective is promoted; no receiver/injection authority is granted; no phone hardware claim is made.
