# LP3 pinned tokenizer metadata-only contract probe — 2026-10-27

Preregistered at `077fef4cc6277766d9c86e94925abd2532d6ec70` before this workflow. Exact parent `5bf412533ecaf8115a84f90beed03ebe5c514206` preserves original failed native Actions `40523353369` and its raw ZIP `2ce6055baa085ffb4107629cef105242292bb8b006a31f682721e46c3be9d8af`.

The isolated workflow downloads **only pinned tokenizer/config metadata**, not the 350M model weights, and inspects actual `apply_chat_template` return type/nesting, normalized token lengths and `encode` answer lengths for two synthetic prompts. No model load, training, optimizer or user data. **CI pending at report creation**. Next: read actual metadata evidence; only then design a separately documented source fix and new bounded real-master compatibility run. The original failed attempt stays failed.

No LP3 utility, JEPA, STEP2/B3/BJ1, Age or Redmi promotion; all negative gates unchanged.
