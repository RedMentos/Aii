# Run160 BodyTrainPort GGUF tensor-type verification protocol

Base `c282a881205bd1a14268297eded3c8a642e53bca`. Owner Run160 only new GGUF metadata scanner, tests, workflow, proof. Do not edit frozen `v13/body_training.py`, Runtime, models, registered cohorts, train masters or any gate.

Risk: the optional no-requantizer exception in `inspect_train_port` trusts descriptor-supplied `fp32_inference_parameter_ids` without independently checking the inference GGUF tensor dtypes. This does **not** grant training authority (remains 0) but a self-asserted FP32 list can make a port appear bound. New read-only scanner checks actual GGUF v3 tensor-info type for claimed IDs, fail-closed for missing/quantized claims.

GGUF primary specification: https://github.com/ggml-org/ggml/blob/master/docs/gguf.md (v3 header, metadata types, tensor name/dims/ggml_type/offset). Synthetic tests locally 8/8 PASS, compileall PASS, 500 random malformed prefixes rejected. Local exploratory tests predate this protocol; do not call them preregistered native proof.

CI next: fetch **bounded first 8 MiB only** of pinned B1 and B2 GGUF revisions from `specs/models.json`; require HTTP Range or bounded streaming; parse header and tensor types; **do not claim full SHA verification** or model availability from a prefix. Never execute a native model, modify weights, or grant train/JEPA authority. If source unavailable, record failed prerequisite and continue.

All original gates stay STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, DS2 H2 FAIL, V13 INCOMPLETE. Native train master/runner/EMA/requantization/retention and Redmi remain unproven.
