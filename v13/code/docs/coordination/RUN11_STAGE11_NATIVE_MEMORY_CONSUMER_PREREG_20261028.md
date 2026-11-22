# Run11 stage11 native source-consumer prompt ablation — prereg 2026-10-28

**Owner:** GPT-6 independent child of #872 source `6862310c72db09522aaeb8da0817013c5b475c54`. Original 20-stage native run 40649812006 stage11 **FAIL** preserved. Model/source/seed pins and all negative gates unchanged. This is **consumer-only**, not a new learned retriever or production prompt change.

**Observed original failure:** C3 (LFM2.5-350M) and B1 (LFM2.5-1.2B) both received the exact source-backed correction `400 Euro` in system context and completed native generation, but their answer texts omitted `400`. Stage11 checks `native_language_answer_uses_human_source` and `native_detail_answer_uses_human_source` were false. Source transport succeeded; native consumer failed. Original stage remains RED.

**Question:** Can a small C3 reliably use source-backed user corrections if the same verified source is rendered in a simpler explicit form instead of nested JSON? Does that improve answer utility without unrelated-source contamination or blind caching?

**Registered design:** 8 fresh synthetic project facts, 4 English and 4 German queries, generated deterministically with Python seed `2801028`, no original Kelmo16 test reuse. For each query, create a real V13 human correction MemoryRecord with SourceRef and read-back equality, no weight learning, and use the *same* actual pinned C3 GGUF with deterministic seed `13`, max 64 tokens, separate calls:
- `json_baseline`: original prompt framing with source-backed correction in JSON.
- `source_first`: concise topic/value source text plus explicit instruction to use only relevant human correction.
- `no_source`: negative control, no correction; model must not invent the withheld number.
- `wrong_topic`: negative control, a real correction from another project explicitly labelled unrelated; model must not use it for the current project.

**Scoring (fixed before native run):** Exact standalone expected numeric amount in answer for positive arms; no expected number for no-source; no other-project value for wrong-topic. Compare per-language rates; no claims from prompt delivery alone. Candidate supports future opt-in only if `source_first` improves at least **0.20 absolute** over JSON on 8 paired cases, has **0/8 wrong-topic leaks** and **0/8 withheld expected-value inventions**. Otherwise `CONSUMER_PROMPT_GAIN_NOT_SUPPORTED`. Even a pass proves only local consumer rendering on synthetic facts, not Stage11 original acceptance, retrieval learning, STEP2, JEPA or Redmi.

**Evidence:** Save all prompts, generated raw answers, native runner metrics, actual installed model hash, SourceRefs, seed and per-arm checks to JSON + SHA256 manifest. Native job serialized in existing `v13-run11-age0-native-endtoend` group, no concurrent heavy native owner. Source/runner/weights unchanged. Next command: implement isolated collector and focused scorer tests, run pinned native workflow, close and independently hash-verify artifacts. No gate promotion.
