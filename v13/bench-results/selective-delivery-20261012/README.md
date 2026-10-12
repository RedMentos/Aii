# WP-T9 rest: fact as trace OR exact block, not both (native C3, paired, 2026-10-12)

Script `code/scripts/selective_delivery_bench.py`, frozen corpus `code/scripts/selective_delivery_corpus.py` (40 invented facts, 40 paraphrases, 40 near-miss questions, 12 retention probes). Preregistered before the run: `code/docs/proofs/selective-delivery-20261012/preregistration.json` (commit `05edcf9`). C3 = LFM2.5-350M Q4 (`3d10b6ab…`) served by the patched `llama-server-mem` (built by `v13.memory_server.build` from the llama.cpp tree vendored in PyPI `llama-cpp-python 0.3.36`, because the GitHub source archive is blocked here). Trace = `SparseMemoryAG6Trainer` on 20 of the 40 facts (keyed slots + entity guard, keys written in the live system context on the dequantized Q4 weights), V13SMEM1 `.bin` sha256 `cb079909…`, training 525 s, torch eval: learned 95 %, KL to base 0.137, no probe forgotten. All 40 facts stay in the exact store. One greedy answer per question, live system message of `runtime._turn`.

| arm | facts | paraphrase | near-miss leak | probes | prompt tokens | exact blocks/turn |
|---|---|---|---|---|---|---|
| base | 0 % | 0 % | 0 % | 83 % | 193 | 0 |
| exact | **97.5 %** | 52.5 % | 57.5 % | 83 % | 253 | 2.08 |
| trace (20 facts) | 47.5 % (95 % of the 20) | 20 % | 17.5 % | 92 % | 193 | 0 |
| combined | 85 % | 55 % | 55 % | 83 % | 253 | 2.08 |
| selective | 87.5 % | 45 % | 50 % | 92 % | 223 | 0.92 |

**Preregistered verdict: SELECTIVE_DOES_NOT_WIN.** Against exact on facts + paraphrases selective has 2 wins / 9 losses (criterion: losses ≤ wins). It does meet the other three criteria: leak −7.5 points, −30 prompt tokens per turn, no extra forgotten probe.

**Why.** (Corrected after per-slot analysis of the audit records; the status `OBSERVED_NATIVE_WRITES` on all rows only means the audit observed the request, not that slots fired.) Questions with ≥1 applied slot: trace arm facts 20/20 in trace, 2/20 outside; probes 1/12. In combined the exact block names other trace facts and the trace then fires on 14/20 facts outside the trace (selective: 4/20). The 9 selective losses vs exact come from two causes: (1) cross-fact interference between similar keys: the 'favourite dish' / 'favourite book' slots fire on 'favourite colour' and 'favourite flower' and the model answers "Your favourite dish"; (2) the trace fires on its own fact but yields a wrong or missing value where the exact block was right (dish → "Thessalonica", tea → "chamomile", bird → "blue jay", two paraphrases not carried at all). Combined is again worse than exact (2 wins / 6 losses), as in `fast-trace-20261010` (7/8 vs 8/8), now on a 5× larger corpus.

**Consequence.** Keep exact delivery. AG6 `auto` keeps not choosing the sparse trainer. No runtime change (SourceHandoff freeze); nothing activated. A next attempt needs (a) key separation for same-frame facts ("favourite …") so a slot only fires for its own fact and (b) trusting the trace only where it is verified (e.g. dedupe only for facts whose trace answer passed a held-out check) before dedupe can pay off; the prompt-token and leak gains of selective are real and worth that.

**Evidence.** `summary.json` (all aggregates, binding with binary/library/model/trace/corpus/script hashes), full report with every answer and native firing record in `report-parts/` (sealed, restore with `scripts/sealed_storage_parts.py restore --manifest report-parts/manifest.json --out report.json`, sha256 `18aba7e1…`), trace artifact in `trace-bin-parts/` + `memory-…bin.items.json`, `trace.json`, server logs (`*.server.log.gz`), `run.log`. `setup-failure-no-gguf.log` is the first start that stopped before any answer (Python package `gguf` missing); it is kept, not counted.

**Claim limits.** Linux x86_64 cloud CPU, not Redmi; invented facts with lexical answer keys; one greedy answer per question; trace holds 20 facts only; runner source from the PyPI-vendored tree (same route as WP-S6), not the GitHub archive hash.
