# LP3 pinned tokenizer metadata-only contract probe — 2026-10-27

Preregistered at `077fef4cc6277766d9c86e94925abd2532d6ec70` before this workflow. Exact parent `5bf412533ecaf8115a84f90beed03ebe5c514206` preserves original failed native Actions `40523353369` and its raw ZIP `2ce6055baa085ffb4107629cef105242292bb8b006a31f682721e46c3be9d8af`.

The isolated workflow downloads **only pinned tokenizer/config metadata**, not the 350M model weights, and inspects actual `apply_chat_template` return type/nesting, normalized token lengths and `encode` answer lengths for two synthetic prompts. No model load, training, optimizer or user data. **CI pending at report creation**. Next: read actual metadata evidence; only then design a separately documented source fix and new bounded real-master compatibility run. The original failed attempt stays failed.

No LP3 utility, JEPA, STEP2/B3/BJ1, Age or Redmi promotion; all negative gates unchanged.


## First metadata-only attempt — preserved FAIL

Actions `40523811633`, exact source `780301db91a87dfb13c0d135be87f9c016976f6b`: **FAIL before tokenizer shape measurement** because the isolated dependency list omitted `jinja2`, required by `apply_chat_template`. Raw artifact ID `12742244570` (no valid shape receipt). This is an environment prerequisite, **not** evidence that the model or tokenizer is incompatible. Next software-only retry pins `jinja2==3.1.6` while retaining this failure.


## Corrected metadata-only attempt — PASS

Actions **40524006855**, exact executable `319f468779d54f2164e408b38d21bf078980917b`, **PASS** after pinned `jinja2==3.1.6` prerequisite. Official pinned tokenizer returns **`BatchEncoding`** (`has_input_ids=true`), not a flat `list[int]`. Both synthetic chat-template prompts normalize to **17 tokens each**, so no padding is needed; first-answer target lengths are **4 and 3** tokens, so the preregistered first-token-only CE remains necessary. No model loaded or training performed. Privacy scan CLEAN, diff check PASS. Artifact **12742692896**, ZIP SHA256 `ea9c457364a4b26f0a838ed24f1b8d306c7ffb21caf0b872ed2cbb3c5cce1b85`; independently downloaded, CRC PASS and JSON values checked, private backup verified. Next: new explicit preregistered native retry with `return_dict=True, return_tensors='pt'` and `input_ids[0]`, preserving original native FAIL. No utility or Age promotion.
