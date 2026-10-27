# Run629 prereg — Run628 C3 native loader dependency compatibility retry

Date: 2026-10-27 UTC. Exact parent Run628 PR #623 head `3738ea7f9ecc959c09ac94a2afe77f6f337abd22`. New child review branch only; source, model, cohort, seed, trainer and negative gates frozen.

## Original observed failure (not erased)

Run628 exact source Actions run 40420000984 (commit `4eabc8c0f4d983e0954aa7bfc0290dfff5c40f65`) concluded FAILURE. Original 15-file raw artifact 12697866817 ZIP SHA256 `62663422b5fb1be210364a12121bd1342ccbc2cee35c3b1c41a9feb75bbbfe44`; all 14 inner SHA256 checks verified. SOURCE_TEST=0 (4/4), DEPS=0, DOWNLOAD=0 (official model SHA verified), PRIVACY=0, TRAIN=1. Actual Python traceback: `LlamaForCausalLM.__init__() got an unexpected keyword argument 'dtype'` from frozen `v13.lora_trainer.LoraTrainer._load` calling `AutoModelForCausalLM.from_pretrained(...,dtype=torch.float32)` under pinned transformers 4.51.3. No optimizer step, no adapter and no native learning proof. Failed original is preserved privately at `/V13-Checkpoints/2026-10-27/Run628/Run628-failed-raw-40420000984.zip`.

## Bounded repair and prospective check

Keep original Run628 `COHORT.json` Git blob `7bf74a8b9de4f7765005093e4cb758da00b9ec0b`, master revision `12fd25f77366fa6b3b4b768ec3050bf629380bac`, master SHA256 `5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c`, training script Git blob `ed2d97cc5249e9eff343792008b41e12d60820fb`, trainer blob `49a752879ae5d19391963742a0f042e740edb2cc`, and original prereg unchanged.

Change *only the isolated CI dependencies* from transformers 4.51.3 to 4.56.2 and huggingface_hub 0.30.2 to 0.35.3 (4.56 supports `dtype`, official Hugging Face Transformers PR #39782 / v4.56 release). Retain torch 2.5.1+cpu, peft 0.15.2, gguf 0.16.3, safetensors 0.5.3 and numpy 2.2.6. Trigger on this child branch. Use the exact existing Run628 source checks, SHA-closed raw artifact, four negative controls, master download hash, 2-step real CPU LoRA fit and privacy scanner. No new training code or model swaps.

**Predeclared success:** dependency install, pinned master verification, source negative tests, native fit/export and privacy all exit zero; proof records 2 optimizer steps, finite CE/heldout KL, nonzero LoRA-B, GGUF/PEFT hashes, and original negative gates. On any failure retain raw, mark FAIL, diagnose without changing cohort or retroactively tuning metrics. No Redmi, deployed llama.cpp, B1/B2, Body-JEPA, STEP2 or V13 completion claim. All model/age/approval gates stay off.
