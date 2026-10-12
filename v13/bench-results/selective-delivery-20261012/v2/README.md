# Selective delivery v2: dedupe only for verified trace facts (2026-10-12)

Script `code/scripts/selective_delivery_v2_bench.py`, preregistered (`code/docs/proofs/selective-delivery-20261012/preregistration-v2.json`, commit `2c446af`). Same corpus, same native binary/model and the same v1 trace (`cb079909…`). Verification pass: each of the 20 trace facts asked once with its stored question, trace only. 19/20 verified (fact 8 "favourite dish" failed).

| arm | facts | paraphrase | near-miss leak | probes | prompt tokens |
|---|---|---|---|---|---|
| exact | 97.5 % | 52.5 % | 57.5 % | 83 % | 253 |
| selective (v1 rule) | 87.5 % | 45 % | 50 % | 92 % | 223 |
| selective_verified | 87.5 % | 45 % | 50 % | 92 % | 224 |

**Preregistered verdict: SELECTIVE_VERIFIED_DOES_NOT_WIN** (2 wins / 9 losses vs exact; identical outcome to v1 rule, 0 differences on recall). The exact and selective arms reproduced v1 answer for answer (deterministic, all 264 answers identical).

**Reading.** Trace-only verification without context does not predict how the trace behaves next to an exact block: "favourite book" was verified alone but still lost in the selective context, and the one fact it removed (dish) was not decisive. The remaining losses are same-frame key interference on facts outside the trace. Deduping by verification is therefore not enough; the trace keys need separation (or a firing check in the actual delivery context) first.

**Consequence.** Keep exact delivery; nothing activated; runtime unchanged.

Evidence: `summary.json`, sealed full report `report-parts/` (sha256 `06a79f5c…`), server logs, `run.log`. Claim limits as v1; verification used the stored fact questions, so the facts set is not unseen for this arm.
