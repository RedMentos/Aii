# P2 C3 receiver-learning research gate — primary sources, NO training (2026-10-29)

Owner: GPT-6 isolated V13 review. This is an **implementation research note**, not a new training registration, model download, native proof or authorization to activate learned weights. Canon `V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` remains binding, including B1/B2 learning, JEF/C2, Context OS, Callosum, Dream/Sleep, Age0 RECORD_ONLY and all negative gates.

## Primary source facts and non-equivalences

- Official LiquidAI `LFM2.5-350M-Base` is a pretrained base intended for fine-tuning: https://huggingface.co/LiquidAI/LFM2.5-350M-Base. The separate `LFM2.5-350M` is instruction-tuned: https://huggingface.co/LiquidAI/LFM2.5-350M.
- Official LiquidAI GGUF model card https://huggingface.co/LiquidAI/LFM2.5-350M-GGUF explicitly distinguishes `LFM2.5-350M-QAD-Q4_0.gguf` from ordinary `LFM2.5-350M-Q4_0.gguf`: QAD is quantization-aware distillation, not merely a post-hoc quantization of the instruction checkpoint. The **currently pinned C3** in HB1b/P0X uses QAD SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`. Therefore LoRA trained on Base or instruction HF master is **not proven compatible** with the QAD GGUF. Do not import a master adapter into production C3 without source/weight mapping and native receiver validation.
- Official Transformers LFM2 docs https://huggingface.co/docs/transformers/model_doc/lfm2 show `Lfm2ForCausalLM` with supervised `labels` and trainable forward pass; official PEFT docs https://huggingface.co/docs/transformers/peft cover LoRA adapter-only training. These establish a candidate software route, not proven training success or mobile performance.
- Preserve original licenses, model revisions, source and seed hashes. Pin HF master commit, tokenizer/config SHA, license text, PEFT/Transformers/PyTorch versions and adapter target module names from the actual loaded module graph before any training.

## Next substantive P2 implementation package, conditional on P0X source-arm evidence

1. **Training corpus:** create a new, prospectively registered, disjoint `P2X` synthetic source-composition training set (project IDs, family seed, surfaces and hashes separate from the frozen P0X 150 heldout). Include B1-only, B2-only, both-exact, foreign-shuffled and no-source examples with correct action/UNKNOWN labels. No P0X answer keys or exact heldout source text in training/calibration. Keep a separate independent validation set beyond P0X if feasible.
2. **Master provenance gate:** fetch pinned HF instruction master and its license into isolated CI; verify SHA256 and correspondence to QAD C3 before asserting transfer. If correspondence cannot be established, train/evaluate the HF master **as a separate cohort**, with QAD native baseline untouched and no production adapter activation.
3. **Training protocol:** default-off LoRA with frozen base, no live V13 age authority, no online JEPA or B3 latent activation. Supervised answer tokens only, deterministic seed and optimizer, full loss/gradient/adapter hash ledger, resource admission and failure retention. Verify no base-weight changes and that adapter unload restores baseline.
4. **Independent evaluation:** on frozen P0X 150 tasks, compare no-adapter vs adapter for exact source, single source, no source and foreign shuffled. Require actual gain over C3-only **and** false-commit controls, plus retention/non-regression. A synthetic gain alone cannot promote STEP2/B3/Body-JEPA/LP3/Redmi/V13 completion.
5. **Operational handoff:** if training path blocked (license/master mismatch, RAM, unsupported modules), record it and pursue Context OS / JEF / B1/B2 integration packages rather than iterating only on helper scaffolding.

Current 600-call native source-arm owner at writing: run `40841374171`, PR #1066; wait for closed evidence before choosing whether P2 training is highest priority. Remaining platform budget UNKNOWN.
