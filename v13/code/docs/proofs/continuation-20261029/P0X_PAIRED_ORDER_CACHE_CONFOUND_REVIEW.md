# P0X 600-arm static order/cache confound review (2026-10-29, before native result)

Independent review of frozen source code only; original 600-call run #40841374171 was still in progress when this note was written. No arm outcomes or score inspected.

The preregistered source-arm plan in `scripts/p0x_c3_source_arms.py` fixes `ARMS=("b1_only","b2_only","both_exact","shuffled")` for **every** one of the 150 projects. The native executor uses one serial C3 `RunnerPool`; frozen `v13/runners.py` sets llama-server `cache_prompt=True` and `id_slot=0` on generation requests. Correct prefix-cache implementation should be semantically transparent, so this is **not evidence of actual cross-request leakage**. Nevertheless, arm and within-project call position are perfectly confounded, and cache state is not experimentally varied.

Consequently, even if `both_exact` improves, this single fixed-order run alone does not identify a purely causal B1/B2 source effect against call-order/cache effects. Preserve the original run and preregistration unchanged. If the result merits follow-up, separately preregister a **new independent control cohort** with balanced/Latin-square arm order and a fresh-runner or `cache_prompt=False` ablation, preserving all original hashes and results. No silent resampling or reclassification.

The frozen C3-only baseline returned `NONE` on all 150 prompts (50 exact only by oracle class balance; 100 wrong commitments), so baseline headroom 100 is necessary but not sufficient to establish source utility. The matched-pair script in this review PR remains descriptive and must not promote STEP2, B3, Body-JEPA, LP3, jepa_weight, Redmi, or V13 completion.

## Primary-source check

The official llama.cpp server documentation (`ggml-org/llama.cpp/tools/server/README.md`, https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) documents that `cache_prompt` reuses the shared prefix and **may cause nondeterministic results** because logits are not guaranteed bit-identical when prompt processing batch sizes differ. This supports a reproducibility caution, **not** a claim of KV-cache cross-request data leakage. The current V13 runner source explicitly sends `cache_prompt=True` and `id_slot=0`; this source audit is static and does not independently establish cache hit rates or causal bias for the pinned b10964 binary.
