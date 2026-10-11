# C3 candidate benchmark (WP-S1 / WP-G / WP-V3), cloud, 2026-10-09

Script: `code/scripts/c3_candidates_bench.py`.

**Setup**
- Runner b10964, 4 threads.
- Production V13 system prompt + answer rules.
- Production decoder: `guards.C3_DECODER`, anti_echo, seeds 13/14/15.
- 34 scored items × 3 seeds, plus 4 open questions for echo.
- Exact checks only, no model judge.

| Model | Overall | Grounded value | Abstain | Format | Rewrite | Digest recall | Decode tok/s | Peak RSS |
|---|---|---|---|---|---|---|---|---|
| LFM2.5-230M (installed C3) | 64 % | 97 % | 6 % | 33 % | 100 % | 83 % | 144 | 383 MB |
| **LFM2.5-350M** | **73 %** | 97 % | 6 % | **72 %** | 92 % | **100 %** | 104 | 519 MB |
| Gemma-3-270M-it | 17 % | 3 % | 22 % | 6 % | 17 % | 58 % | 95 | 704 MB |
| Qwen3.5-0.8B (B2 body) | 79 % | 90 % | **67 %** | 61 % | 83 % | 92 % | 39 | 1950 MB |

**WP-V3 (anti_echo vs. legacy, same seeds)**
- Overall accuracy: 230M 64 vs. 63 %, 350M 73 vs. 76 %.
- Query echo on open questions is low with both decoders (0.02–0.05).
- No clear difference; anti_echo stays the default.

**Recommendation**
- LFM2.5-350M is the better C3: format following more than doubles, and digest recall is 100 %.
- Cost on the cloud CPU: about 28 % slower decoding and +136 MB RAM.
- Gemma-3-270M is unusable with this prompt.
- Qwen3.5-0.8B is the most reliable, and the only one that abstains, but 2 GB RAM and 39 tok/s rule it out as C3 on the Redmi (it stays B2).
- Abstention is weak for both LFMs: they almost never say "not in the source". That is a consequence of removing the abstention phrase in WP-KAL2 and remains an open prompt or training topic.

**Not done:** C3 is not switched over. That needs the Redmi RAM/latency measurement (WP-R) and your decision.
