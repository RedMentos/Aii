# WP-G G1B: Age-0 gist view vs fixed/event segments with a real B2 (2026-10-12)

Script `code/scripts/gist_utility_bench.py`, preregistered (`code/docs/proofs/gist-utility-20261012/preregistration.json`, commit `8b45c73`). B2 = Qwen3.5-0.8B Q4_0 (pinned hash), llama.cpp b10964, thinking off, temperature 0, `OFFER_SCHEMA` JSON, B2 instruction text from `cognition.offer`. 36 synthetic project memos (2.2–2.8k chars) with an early owner fact, a middle budget fact and a late deadline revision; one question per memo. All three views carry the whole text; they differ only in cutting (runtime source refs included as the runtime sends them).

| view | hit | owner / budget / deadline | stale old deadline | quotes all exact | quote holds key | prompt tokens | s/offer |
|---|---|---|---|---|---|---|---|
| fixed960 (runtime default) | **94.4 %** | 100 / 100 / 83 % | 2 | 66.7 % | 88.9 % | **915** | **8.5** |
| event960 (WP-N8) | 80.6 % | 100 / 67 / 75 % | 3 | 80.6 % | 66.7 % | 1501 | 11.7 |
| gist (Age 0, 8 tok / 12 slots) | 86.1 % | 100 / 83 / 75 % | 3 | 80.6 % | 86.1 % | 1951 | 13.9 |

**Preregistered verdict: GIST_NO_GAIN.** Gist vs fixed960: 1 win / 4 losses on hits and 2.1× prompt tokens (criterion ≤ 1.1×). The one criterion it meets: more offers with only exact quotes (80.6 % vs 66.7 %).

**Reading.** At this text length the gist view costs most of its extra tokens on per-slot SourceRef metadata (12 slots instead of 3 segments), and the coarser merged old groups lose some middle facts (budget 83 % vs 100 %). The better quote validity suggests short slots help exact quoting, which is worth keeping in mind for the source-handoff work. `:gist` stays SHADOW; runtime unchanged.

**Claim limits.** Linux cloud CPU, not Redmi; synthetic memos; one greedy B2 offer per memo, no B1, no C3 answer, no re-entry; texts fit in 3 segments, so the multiscale coarsening for much longer texts is not tested here. Evidence: `report.json` (every offer), `run.log`, `server.log.gz`.
