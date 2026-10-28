# Native model provenance check — primary-source research, 2026-10-28

No model artifact was downloaded or executed in this automation. This is a provenance reminder for the future **separately preregistered** TP/TC/SP/SC native run; it does not replace exact hash verification or license review.

- Official Liquid AI model card: https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF — repository labels its license `lfm1.0`, and explicitly distinguishes `LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf` from the post-training-quantized `LFM2.5-1.2B-Instruct-Q4_0.gguf`. The exact filenames and SHA256 matter; these are not interchangeable proof artifacts.
- Official Liquid AI 230M GGUF model card: https://huggingface.co/LiquidAI/LFM2.5-230M-GGUF — `lfm1.0`, QAD file `LFM2.5-230M-QAD-Q4_0.gguf`. Preserve its independent C3 role, tokenizer/chat template and exact hash.
- Liquid AI primary technical release, 19 August 2026: https://www.liquid.ai/blog/qad — describes QAD vs PTQ performance and deployment. Vendor benchmark statements are not V13/Redmi evidence.
- `lfm1.0` is a custom license, not an assumption of unrestricted redistribution. Review the exact LICENSE from the pinned model revision before redistribution or bundling. Public review branches must contain no model weights, private user data or credentials.
- The **two-distinct** TP/TC experiment requires B1 and B2 actual weight-file SHA256 to differ. Age-0's two roles using the same LFM GGUF do not satisfy that control; a distinct B2 weight and its license/provenance must be pinned separately. Shared-body SC/SP deliberately use the same B1 weight with distinct state/prompt policies. Never silently substitute a different quantization, revision, runner or seed.

Open: exact B2 distinct-model revision/license, exact C3 and runner/library hashes, native installation owner/cgroup, Redmi measured thermal/energy, and a new preregistration of this collector's final tested source. No native proof and no STEP2/B3/Body-JEPA/age promotion.
