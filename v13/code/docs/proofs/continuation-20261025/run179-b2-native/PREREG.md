# Run179 — prospective pinned B2 native tap provenance (2026-10-25)

Base: verified Run178 review branch `d9170cd07ab37843d25055e9e03136a527337f1f`. This registration is saved **before** any Run179 native model execution. File owner: new `scripts/run179_b2_native_tap_probe.py`, `tests/test_run179_b2_native_tap_probe.py`, this proof and dedicated CI only. Frozen Runtime, Run177 B2 correction, model registry, source, weight, age and approval gates are untouched. No simultaneous heavy native/model jobs: CI must use the existing shared serial concurrency group `v13-native-c3-run131-serialized` with `cancel-in-progress:false`.

## Immutable inputs and source authority

- Registered B2 model: `ggml-org/Qwen3.5-0.8B-GGUF` revision `8fea620810c4afa23dd6443f999a48574c1611a3`, `Qwen3.5-0.8B-Q4_0.gguf`, **563036064 bytes**, SHA-256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`; Apache-2.0 per `specs/models.json` (not a new selection).
- Registered runner: `ggml-org/llama.cpp` tag `b10964`, Ubuntu x64 release archive **16825086 bytes**, SHA-256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`, source tag/commit bound by existing registry. Existing `v13/code/v13/runners.py` Git blob `37bf8e1c0222d4148dfbc3d2aedbef0c03adeac5`, model spec Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`. No model or runner swap.
- Inputs are exactly 3 public synthetic English strings: `The blue robot moves left.`, repeated verbatim, and `The red robot moves right.`; `max_tokens=64`, `context_tokens=1024`, `threads=2`, `native_cache_ram_mb=0`, `native_ctx_checkpoints=0`. Single B2 read-only tap runner. No trainer, receiver, injection, user content or private fixtures.

## Prospective check and negative controls

Require exact model/archive hashes **before launch**. `LlamaRunner.tap()` on the actual native Qwen weights must return 1..64 token IDs and one finite nonzero **1024D** vector per token; `metrics.tap_id='qwen35.result_norm.final.v1'`, `role='B2_GIST'`, `CAN_LATENT_TAP=True`, `CAN_TRAIN_BODY=False`, `CAN_LATENT_INJECT=False`. Repeated identical prompt must have identical token IDs; changed prompt must change token IDs. Record the maximum repeated-vector absolute delta, without promoting determinism unless independently bounded. Verify the process unloads in all paths. Raw stdout/stderr and server logs must be retained even on failure; nonzero CI status must remain nonzero. Model and archive SHA-256 are checked in CI and logged.

This is **read-only native tap provenance only**, not B2 learning, not JEPA, not a B3 receiver, not cross-body utility, not Redmi, not full V13. Software tests may pass without the model; they cannot replace the registered native result. The original Run173 full-suite FAIL (orphan child, optional fixture error) and Run177 generic phone-source hash mismatch remain visible and separate.

## Gates and next action

`STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`. No gate promotion from any Run179 result. If network, disk, server ABI, or Qwen token embedding mode fails, preserve the failure and investigate without changing pins or silently altering test criteria. After source/registration checkpoint, start the serialized native CI and independently inspect its closed raw logs and provenance before considering any next Body-JEPA work. No rejected Drive destination.
