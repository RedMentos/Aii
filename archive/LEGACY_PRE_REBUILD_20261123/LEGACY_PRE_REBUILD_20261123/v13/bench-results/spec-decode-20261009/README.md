# §22.6 Speculative decoding: cloud measurement 2026-10-09

Setup: runner llama.cpp b10964, 4 threads, greedy decoding, 4 fixed prompts with 128 tokens each. Target B1 is LFM2.5-1.2B Q4_0. Script: `code/scripts/spec_decode_bench.py`.

| Config | Tokens/s | vs. base | Draft stats | Output identical | Peak RSS |
|---|---|---|---|---|---|
| baseline | 37.5 | 1.00 | – | – | 1.46 GB |
| ngram-simple | 34.3 | 0.92 | none reported | yes | 1.46 GB |
| draft LFM2.5-230M (`-md`, n-max 4) | 36.9 | 0.98 | none reported (`draft_n` missing) | yes | 1.78 GB |

**Result.** The server loads the draft model, but speculation never takes effect: there are no draft/accept counters in the timings and no gain. The likely cause is the same one found in WP-N7: LFM2 and Qwen3.5 are hybrid/recurrent, and llama.cpp cannot roll back their state to an earlier point. Rolling back is exactly what a rejected draft requires. The draft model costs +330 MB RAM for nothing.

**Decision.** Speculative decoding stays off for the V13 bodies. It could be re-evaluated with a pure-transformer target body or a later runner that supports state rollback for hybrid models.
