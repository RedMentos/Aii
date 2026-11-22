# Smallest native trainable BodyPort slice — 2026-10-08

This audit proposes a bounded next experiment within the existing BodyPort. It does not change Canon, production code, gates or installed model weights. No native inference or training was executed for the audit. Compilation of an isolated prototype is separately recorded; compilation is not a TrainRunnerProof.

The immutable source is `docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`, SHA-256 `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`. Relevant requirements are W4–W6, §19/19H, §22.3, IH-H24, §89, §90, §91 and STEP 5/6C. Native parameter authority remains **zero** until the exact path has its own measured proof, existing individual approval and actual target-phone validation.

## Concrete result

The smallest installed native parameter slice is the final LFM2 RMSNorm scale, **`token_embd_norm.weight`**, not a fictional sparse expert. Installed C3 contains 1,024 native FP32 scale parameters. Changing this vector changes the native full-vocabulary decoder projection at every output position while leaving the quantized trunk and tied token/output weights frozen. Its masters can occupy 4,096 bytes, but total forward/backward RSS includes the actual model, recurrent/attention state, graph, logits and allocator buffers; 4 KiB is not a memory prediction.

This is a real dense native weight-update experiment. It is not MoE training, a general language-learning guarantee, a trainable receiver bridge or an adequate way to store arbitrary user facts. A shared 1,024-dimensional scale can damage unrelated outputs, so fixed old-task retention and actual output consumers are mandatory. The more immediate serving improvement remains the separately audited live-prefill port and native execution of the existing approved external delta; moving that delta into C++ must not be relabelled as native body training.

## Exact installed shapes and pinned source

The audit used the already verified b10964 source archive (`b29c606e2`, archive SHA `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe`) under `native/tmp/audit/llama.cpp-b10964`. Bounded GGUF header reads used the existing `scripts/audit_native_ports.py::inspect_gguf` implementation with an in-memory selection extended to the actual LFM2 norm name. No weight payload was loaded for those reads.

| Installed artifact / tensor | Header shape / type | Implication |
|---|---|---|
| C3 `LFM2.5-230M-QAD-Q4_0.gguf` | 229,693,184 stored parameter elements; 132 tensors | Dense fallback, not sparse expert execution |
| C3 `token_embd_norm.weight` | `[1024]`, GGML type 0 = F32; relative payload offset 55,050,240 | Exact smallest native scale slice; 1,024 trainable elements |
| C3 `token_embd.weight` | `[1024,65536]`, type 14 = Q6_K | Tied frozen vocabulary projection when `output.weight` is absent |
| C3 `blk.13.ffn_norm.weight` | `[1024]`, F32 | Earlier slice requires gradients through the last FFN; defer until final norm path is proved |
| B1/B2 shared immutable artifact `LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf` | 1,170,340,608 stored elements | Role-specific mutable masters must remain separate |
| B1/B2 `token_embd_norm.weight` | `[2048]`, F32; offset 110,100,480 | Possible later 2,048-element role-specific slices, not evidence of complementary learning |

The previously verified installed hashes are C3 `e75f83268de11b2a1bcfab5f3b5c5c0c97569ddbbc0990aad88437e45b8ba292`, B1/B2 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, and loaded `libllama.so.0.4.1` `09f62256d92254c0675315423e399f20e24526d8e865146b4c9bc1993f066f50`. An executable must independently hash the actual loaded artifact/library rather than trust these prose pins.

| Exact pinned file / API | Finding |
|---|---|
| `src/llama-arch.cpp:431` | `LLM_TENSOR_OUTPUT_NORM_LFM2` maps to `token_embd_norm`, correcting a historical generic-name mismatch |
| `src/models/lfm2.cpp:39–44` | Loads final scale; missing output matrix duplicates tied token embedding tensor |
| `src/models/lfm2.cpp:277–294` | Final RMSNorm then vocabulary `build_lora_mm`; embedding mode suppresses the projection |
| `src/llama-graph.cpp:1583–1615` | RMS normalization produces `norm`, followed by multiplication by the native scale producing `result_norm` |
| `include/llama.h:1605–1632` | `llama_opt_param_filter`, `llama_opt_init`, `llama_opt_epoch` really exist |
| `src/llama-context.cpp:3391–3454` | Optimizer marks only F32 tensors; excludes token embeddings; an exact-name filter can select final scale only |
| `src/llama-context.cpp:3457–3559` | Epoch labels **every** context token. It cannot silently implement a single human-labelled response-position objective |
| `ggml/include/ggml-opt.h` | Lower-level `ggml_opt_prepare_alloc/alloc`, `ggml_opt_labels`, `ggml_opt_eval`, and gradient APIs exist; alternatively build one loss graph with public `ggml_build_backward_expand` and inspect compute status |
| `ggml/src/ggml.c:6871–6925` | Backward MUL_MAT uses frozen output matrix through `OUT_PROD`; gradient need only reach final scale, not earlier frozen recurrent layers |
| `ggml/src/ggml-cpu/ops.cpp:4492–4580,4645–4690` | CPU OUT_PROD dequantizes frozen Q6_K rows into bounded row scratch and supports that type |
| `examples/training/finetune.cpp:31–42` | Native example forces `LLAMA_LOAD_MODE_NONE` for writable weight pointers, not mmap mutation |

## What the current output head already implements

`v13/output_adapter_worker.py` already trains a **separate external** 1,025-by-2…16 vocabulary-row delta plus calibration temperature. It uses actual frozen 1,024D native C3 states, measured complete 65,536-vocabulary normalization with one unchanged-mass category, explicit immutable human output labels and source-disjoint train/calibration/test. Its current NumPy masters are floating point; native body parameters modified remain zero. It includes sampled finite differences, source-bound permission/approval, support anchors, saved old targets, deterministic repeat, reload, rollback and actual first native token consumption. The subsequent native continuation is unbiased.

The retained 2026-10-07 production proof has 23/23 scoped checks and 26/26 held-out native first-token matches for known greeting/thanks families. That is not full-language adaptation, arithmetic, semantic OOD or current Redmi training proof. The separate tap/baseline/generation processes also do not establish live-prefill/KV continuity. Native porting may remove transport/duplicate work, but it changes neither the objective nor its narrow demonstrated utility.

## Minimal isolated implementation

1. Accept one **already rendered exact native token-ID context** and an explicitly human-labelled first-response token, with immutable context/reference/permission identifiers. Do not train on model-generated answers, prompt tokens, guessed answers or synthetic correctness. Bound context to 512 native tokens and one labelled position per experiment. A missing source binding is a refusal.
2. Load the exact C3 artifact in an isolated CPU context, `LLAMA_LOAD_MODE_NONE`, no LoRA, no embedding mode, no production serving session. Keep the original GGUF immutable. During final ordinary generation prefill, the existing evaluation observer reads raw final `norm` **before** scale multiplication, verifies the exact native final scale handle and frozen tied output tensor from `result_norm`/`result_output`, and copies the one selected row. Do not retain temporary graph-node pointers after graph reuse; permanent model weight handles are valid only while that model is alive. Reject reordered/missing/ambiguous nodes or mismatched shape/operation/name.
3. Build a separate bounded native tail graph: copied raw RMS-normalized state `[1024,1]` (stop-gradient), separate FP32 master `[1024]` (only PARAM), native multiply, borrowed frozen quantized output matrix `[1024,65536]`, full logits `[65536,1]`, one-hot **human first-response** label and one cross-entropy loss. No loss is attached to other prompt positions. Public GGML backward graph creation can provide the 1,024-coordinate gradient with checked computation status; high-level `llama_opt_epoch` is deliberately not used.
4. Start with one bounded SGD step, no momentum and no base optimizer. Preserve original master, gradient, update-norm bound and exact source bindings. Save candidate FP32 scale as a separate atomic file; never overwrite the pretrained GGUF. Apply it only to the isolated context's exact writable scale handle, clear/recompute that context, and measure actual native logits/output. Restoring the old vector is the rollback baseline. A saved master alone does not establish restart: a fresh process must load it and reproduce the same isolated native result.
5. Freeze source/corpus/parameter-path identity before running. The prototype initially only records observations and numeric comparisons; it has no approval, runtime registration or consumer authority. Production import must go through the existing F4/F7 candidate-generation lifecycle, individual approval, source revocation/quarantine and exact model/runner/tensor/shape/precision binding.

No quantized trunk master is needed for this path: the changed slice was already FP32 and stays FP32 in serving. Therefore this experiment must report **quantizer roundtrip NOT_APPLICABLE_TO_THIS_SLICE**, not PASS for updating/re-quantizing Q4/Q6 base weights. A later low-rank adapter is also distinct from training quantized base slices. A real selected quantized-row update would need independent FP32 masters, exact quantization/reload parity and its own proof; none currently exists.

## Gradient exactness is a separate question

Do not label the GGML gradient an exact derivative of deployed quantized arithmetic without testing it. The pinned CPU matrix product converts F32 input activations into a dot-product quantization type (`ggml/src/ggml-cpu/ggml-cpu.c:1273–1355`; Q6_K selects Q8_K in its CPU type traits). The backward OUT_PROD dequantizes fixed weights and multiplies by F32 errors. It does not differentiate through activation-rounding boundaries. The result may be a useful surrogate gradient for a fixed dequantized-weight mathematical model, while actual quantized forward finite differences differ.

The proof must separately retain: (a) independently computed FP64 mathematical reference using frozen dequantized Q6_K rows, complete vocabulary softmax and the raw final normalized state; (b) GGML native gradient; (c) actual quantized tail finite differences at preregistered epsilon values; (d) full native prefill logits before/after. Preserve all mismatches. If exact quantized differentiation fails, declare the actual method as surrogate and keep the exactness gate failed; no tolerance retuning or claim of exact MeSP-style training follows. The isolated prototype must never turn observed loss reduction on one row into a retention/generalization PASS.

## Exact remaining proof obligations

- Native tail versus real C3 prefill logits before update, every finite vocabulary row, exact raw-state/output/tensor mapping and baseline greedy token. Include >128-token and repeated-prefix contexts; changing final scale must not fabricate new context.
- Exact trainable count 1,024, stored frozen count 229,692,160 for this C3 header scope, master 4,096 bytes, SGD momentum 0 bytes; actual graph/activation/gradient/label/logit/allocator bytes and sampled process RSS/PSS separately. No RAM extrapolation from parameter count.
- Source-disjoint labelled fit/calibration/test, actual held-out native utility, fixed old-case retention across unrelated tasks, OOD/support bounds, zero-update equivalence, nonfinite/oversize/tamper refusal. A global scale update affects all output positions and requires a broader retention suite than the existing first-position external delta.
- Cancel/deadline during real forward, native backward and checkpoint; nonzero compute status must abort candidate creation. First-cause/cleanup, no zombie or partial active artifact. Atomic write/crash injection, hash verification, fresh-process resume, exact rollback, original GGUF hash and frozen loaded tensor bytes unchanged.
- Complete §89 TrainRunnerProof fields. Energy/battery/thermal unavailable on Linux are null/open, not estimated PASS. Repeat bounded/sustained tests on the real Redmi before Phone-Learning/commit claims. No gate promotion for compilation, exported symbols or Linux-only execution.

This provides a concrete next native implementation path without replacing existing working heads, claiming sparse access or adding another architectural layer. STEP-0/1/2 utility and source/state integrity remain the current vertical-path priority; deeper native updates are an isolated shadow experiment until those dependencies and this exact proof are complete.
