# Run382 preregistration — native C3 answer utility via instruction-only prompt ablation

2026-10-25. Owner: isolated `v13/code/scripts/run382_c3_prompt_ablation_native.py`, its workflow and this proof directory. Parent Run381/PR376 `340b143b450d17db5c4bba5ce7b936779be16aba` (Run381 Z8d FAIL remains isolated and unpromoted). Existing Run373/PR368 pinned native C3 diagnostic is complete negative (2/4 exact); its original cases and hashes remain unchanged. Active Run377 Context OS/Run378 B3 owners untouched.

**Immutable native prerequisites:** public `LiquidAI/LFM2.5-350M-GGUF` revision `657e078c94084481950a2d555a941481f715536b`, file `LFM2.5-350M-QAD-Q4_0.gguf`, 219312832 bytes, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, LFM Open License 1.0; llama.cpp b10964 Linux x86_64 runner 16825086-byte archive SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`. Retrieve and verify exact bytes; no model weights or native binaries in evidence artifacts. One serialized native runner; no paid cloud, no Redmi claim.

## Fixed A/B experiment, no prompt retuning after measurement

Use real `LlamaRunner.generate` with the existing `BodySolver.SCHEMA` JSON grammar, confidence_field `answer`, seed=13, temperature=0, 512 context, 40 answer tokens, 2 threads, 32MB native cache. No tools, history, memory, teacher or learning. Baseline system prompt is **exactly** `v13.agi.solver.SYS` (`Answer with only the final answer. No explanation, no units, no extra words.`). Candidate system prompt (frozen now): **`Give exactly the requested final result as a single short answer. For arithmetic, calculate the value. For backwards text, reverse every character. For number sequences, continue the numerical pattern. Never explain your reasoning.`**. User prompts identical per arm. Alternate A/B order by item index (even baseline first, odd candidate first). No training/holdout contamination; native run reports generated answer and field token confidence, not gold prompts into Store.

New independent 12 tasks (not Run373's 4):
- Arithmetic: `Compute: 8 + 6 = ?` → 14; `Compute: 5 + 9 = ?` → 14; `Compute: 11 - 4 = ?` → 7; `Compute: 3 * 4 = ?` → 12.
- Backwards: `Write backwards: cat` → tac; `Write backwards: sun` → nus; `Write backwards: lamp` → pmal; `Write backwards: blue` → eulb.
- Sequences: `Continue: 1, 3, 5, ?` → 7; `Continue: 5, 10, 15, ?` → 20; `Continue: 10, 8, 6, ?` → 4; `Continue: 3, 6, 9, ?` → 12.

**Primary PASS only if**: candidate improves exact answers by >=3/12 over baseline, does not regress any of the 3 categories, 24/24 calls finish with native status FINAL and positive answer-field token confidence, model process is reaped with no leftover PIDs, and candidate mean duration <=1.5x baseline. Report all errors, outputs, confidence, timings, RSS and per-category breakdown. If any condition fails, `RUN382_NATIVE_PROMPT_NOT_SUPPORTED` and no prompt promotion; preserve failure. Synthetic/unit test only verifies case disjointness and verdict semantics, not native correctness. Native result only Linux C3 small model; no STEP2/B3/Body-JEPA/jepa_weight/Redmi/whole-V13 promotion.

## Evidence/persistence

Source, runner/model/catalog hashes, exact head, host, raw download receipts, native output and privacy scan go to hashed Actions artifact. Download ZIP, verify CRC/internal SHA and private Library byte-identical backup. Preserve any failure; if blocked, pursue independent canonical work.