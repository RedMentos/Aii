# Native capture recovery after workspace pruning

The previous terminal evidence remains intact: 1875 rows, eleven owned workers, no observed OOM events. Its complete NPZ and full raw responses were not durably uploaded before workspace maintenance removed scratch. They are unavailable; the terminal evidence alone does not recover those arrays.

The durable 736-row archive has been restored into a separate read-only folder. Its original registration, NPZ, and all 46 raw batches match the archived bytes. The original bounded lifecycle wrapper and native capture driver remain unchanged. Only output and historical-prefix folder locations change for this repeat. Inputs, embedding parameters, native binding, training objective, and quality gates remain fixed.

Before registration, restore and verify the original model, launcher, and 19 runtime library entries. Registration performs no model inference. Publish the new registration and the path-only comparison. Inference starts only following RootGO. Both fresh control workers must pass exact numerical invariance and the historical first-16 comparison before any main capture resumes.

Every safe new prefix must be closed from one atomic NPZ read with hash-bound immutable raw responses, losslessly split into parts of at most 1 MiB, and published with a SHA manifest. Preserve the original NPZ and response bytes. Do not claim equality with the previous complete capture until the complete array and raw input binding are actually compared; serialization or request-alias changes must remain visible.

The three training seeds 13/21/34 remain blocked until the actual new dataset SHA is verified on GitHub and RootGO is received. Receiver authority remains zero and learned semantic quality is unproven.

Registration command after resources are restored:

```sh
python3 scripts/bounded_action_jepa_capture.py --register-only --plan /workspace/scratch/5a9214d3f329/v13-work/Aii/v13/code/docs/proofs/continuation-20261011/action-jepa-preregistered-plan-v2.json --sentences /workspace/scratch/5a9214d3f329/v13-work/Aii/v13/bench-results/jepa-ablation-20261010/sentences.json --actions /workspace/scratch/5a9214d3f329/v13-work/Aii/v13/bench-results/jepa-action-20261010/actions.json --model /workspace/scratch/5a9214d3f329/native-audit-cache/models/gist/Qwen3.5-0.8B-Q4_0.gguf --server /workspace/scratch/5a9214d3f329/native-audit-cache/bin/build-mem-b10964/bin/llama-server --out /workspace/scratch/5a9214d3f329/v13-work/Aii/v13/code/docs/proofs/continuation-20261011/action-jepa-bounded-recovery-night --original-capture /workspace/scratch/5a9214d3f329/v13-work/Aii/v13/code/docs/proofs/continuation-20261011/action-jepa-native-capture-night-restored --prefix-archive /workspace/scratch/5a9214d3f329/v13-work/Aii/v13/code/docs/proofs/continuation-20261011/action-jepa-prefix736.closed.zip --check-frozen70 /workspace/scratch/5a9214d3f329/v13-work/Aii/v13/code/docs/proofs/continuation-20261011/step2-webchat-70/report.json --frozen-source-archive /workspace/scratch/5a9214d3f329/v13-work/Aii/v13/code/docs/proofs/continuation-20261011/step2-webchat-70/frozen-source.tar.gz --frozen-source-archive-sha d59ac71c5af559db015e521052f13d00736784ba18eb8c258caf0933d29ee081
```
