# BP1 V2 LoRA native-proof contract cross-review — prospective software-only prereg (2026-10-27)

Owner: GPT-6 independent review; source base `f6d6812a493cc7d2235e97bf16e0324242d1ecd6` on the active BP1 LoRA V2 child chain. This review branch does not modify the owner's branch, production code, native training, datasets, weights, or gates.

Observation before test: `bp1_qad_lora_eval.verify_train_proof` accepts a proof when the 2-step count and trainable count are valid but the declared `metrics.rank`, `metrics.alpha`, `metrics.targets`, `metrics.anchor_weight`, `metrics.final_ce`, and adapter export metadata disagree with the frozen training contract. A byte hash only binds the supplied proof file to the binding; it does not prove that its contents satisfy the source contract. This is a software contract bypass, not evidence of malicious behavior or a failed native run.

Prospective RED: construct otherwise structurally valid synthetic train proof, bind its exact SHA, mutate each frozen metric/export field independently, require `verify_train_proof` to reject. Confirm the current implementation incorrectly accepts at least one case. No heldout source, model, adapter or live server required.

Fix: check the actual native `LoraTrainer.fit` metric fields (rank2, alpha4, ordered v_proj/out_proj, anchor0, jepa0, finite nonnegative CE, two optimizer steps, non-resumed) and `run632_c3_lfm350_native.verify_export` metadata (GGUF and PEFT SHA format, positive GGUF bytes/tensors and LoRA-B tensors/nonzero), while keeping original proof schema and all source/model/seed hashes unchanged. Preserve original negative gates and no authority promotion. Do not reinterpret a declared proof as independently audited raw native evidence.

Evidence levels: synthetic software RED/GREEN only. Original native train Actions 40476209086 was in progress at prereg; do not start competing heavy native jobs. Later independently close original raw exits before any model claim. STEP2 UTILITY_FAIL; B3 L1_FAIL; Body-JEPA UNAVAILABLE; jepa_weight0; Redmi unmeasured; full V13 incomplete.
