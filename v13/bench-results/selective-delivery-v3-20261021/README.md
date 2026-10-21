# Native firing diagnostics + key separation for the fast trace (WP-T9 v3, native C3, 2026-10-21)

Script `code/scripts/selective_delivery_v3_bench.py`, preregistration `code/docs/proofs/selective-delivery-v3-20261021/preregistration.json` (commit `f2f6976`, pushed before training and inference). Same frozen corpus as v1/v2 (40 invented facts, 40 paraphrases, 40 near-miss questions, 12 retention probes), C3 LFM2.5-350M Q4 (`3d10b6ab…`), master LFM2.5-350M (`1c9c77a4…`, = v1). Runner: patched `llama-server-mem` built by `v13.memory_server.build` from the pinned llama.cpp b10964 GitHub archive (`4c96d72c…`; v1 used the PyPI-vendored tree), so both traces were trained fresh and all arms re-ran on one binary.

## 1. Diagnosis (before the prereg, from the v1 audit records)

The v1 report said only "OBSERVED_NATIVE_WRITES". Mapping every audited `fired_rows` entry to its memory id via the `.bin` row map gives which slot fired on which question. v1 foreign firings (a memory that is not the question's own fact): trace 31, selective 42, combined 121. Two causes:
1. **Shared guard words.** The entity guard of "What is my favourite dish?" is {favourite, dish}; "favourite" opens it on "favourite colour / flower / cheese". Same for *play*, *best*, *live*.
2. **Guard context = whole prompt.** An exact block in the system message that names another fact opens that fact's slot ("tortoise" fired on every "name of my …" question in the combined arm).

## 2. Fix candidate (`v13/sparse_memory.py`, `scripts/v13_memory_hook.h`, default off)

- `guard_distinct=True` + `guard_vocab` (the store's fact questions): guard words only where no other fact question shares them (`guard_words`); "favourite dish" → {dish}.
- `guard_scope='last_user'`: the guard sees only the last user turn + assistant header (from the second-to-last `<|im_start|>`), in torch (`scoped_context`) and natively (`v13_new_prompt`). Encoded in the V13SMEM1 header field 6 as `2 + marker token`; 0/1 keep their old meaning, an old binary reads a scoped file as whole-prompt guard (fails toward the old behaviour). Defaults unchanged; tests `tests/test_guard_separation.py` (11, incl. torch guard and header round trip).

## 3. Native result

| arm | facts | paraphrase | near-miss leak | probes | prompt tokens | rows with foreign firing | foreign firings |
|---|---|---|---|---|---|---|---|
| base | 0 % | 0 % | 0 % | 83 % | 193 | – | – |
| exact | **97.5 %** | 52.5 % | 57.5 % | 83 % | 253 | – | – |
| trace_v1 (old guard) | 47.5 % | 20 % | 17.5 % | 92 % | 193 | 24 | 31 |
| selective_v1 | 87.5 % | 45 % | 50 % | 92 % | 223 | 33 | 42 |
| **trace (fix)** | 50 % | 20 % | 22.5 % | 92 % | 193 | **17** | **17** |
| combined (fix) | 87.5 % | 55 % | 57.5 % | 83 % | 253 | 84 | 115 |
| **selective (fix)** | **97.5 %** | 45 % | 52.5 % | 92 % | 223 | 25 | 26 |

Own firing on the 20 trace facts (stored question): 20/20 in both traces. Audit observed every row.

- **H1 KEY_SEPARATION_SUPPORTED** (preregistered): foreign-firing rows 24 → 17, foreign firings 31 → 17; on the 40 stored fact questions 4 → **0**. What remains is near-miss questions about the same thing of another person ("my sister's car", "my cousin's nickname": 14 rows) – word guards cannot separate those.
- **H2 SELECTIVE_DOES_NOT_WIN** (preregistered v1 criteria): selective vs exact 2 wins / **5** losses (v1 rule: 2 / 9; fix vs v1 selective: 4 wins / 0 losses). Leak, prompt tokens (−30/turn) and probes pass. All 5 losses are paraphrases, none from foreign firing any more: the trace fires on its own fact but carries a wrong value (tea "chamomile", bird "blue jay", tortoise answered "Tortoise"), plus 2 paraphrases ("company", "closest friend") where neither the exact block nor the right slot reached the answer.
- Combined is still worse than exact (2 / 5) and still had 84 foreign-firing rows. That pointed to a **native bug in the fix**: the embedding hook of `v13_memory_hook.h` also inserted every decoded prompt chunk into the guard context, so natively the last-user scope only held for the cached prefix (torch was correct). v3 therefore measured `guard_distinct` with an ineffective native scope. Fixed (commit `f09ef8b`: with an explicit, scoped context only generated tokens join), test added, re-run as v3b below. The v3 verdicts stay as recorded.

## 4. v3b: same traces (byte-identical), corrected native binary (prereg `preregistration-v3b.json`, commit `f09ef8b`)

| arm | facts | paraphrase | near-miss leak | probes | prompt tokens | rows with foreign firing | foreign on fact questions |
|---|---|---|---|---|---|---|---|
| exact | 97.5 % | 52.5 % | 57.5 % | 83 % | 253 | – | – |
| trace_v1 | 47.5 % | 20 % | 17.5 % | 92 % | 193 | 24 | 4 |
| selective_v1 | 87.5 % | 45 % | 50 % | 92 % | 223 | 33 | 8 |
| trace (fix) | 50 % | 20 % | 22.5 % | 92 % | 193 | 17 | 0 |
| combined (fix) | 90 % | 55 % | 52.5 % | 75 % | 253 | **17** (v3: 84) | 0 |
| **selective (fix)** | **97.5 %** | 45 % | 52.5 % | 92 % | 223 | **16** (v3: 25) | 0 |

- **H1 KEY_SEPARATION_SUPPORTED** again. With the scope working natively, an exact block no longer opens other facts' slots: combined 84 → 17 rows, selective 25 → 16. No fact question fires a foreign memory in any fixed arm. The rest are near-miss questions about another person's thing (13–14 rows) and two paraphrases sharing a word ("live").
- **H2 SELECTIVE_DOES_NOT_WIN**: unchanged 2 wins / 5 losses vs exact, the same 5 paraphrase losses (wrong or missing trace values, not firing). Combined vs exact now 2 / 4; its losses are garbled spellings when trace and exact block both deliver the same fact ("shakkauka", "rooosbos"), and one more forgotten probe.
## Consequence

Firing is fixed, value quality is not. Keep exact delivery; AG6 `auto` keeps not choosing the sparse trainer; nothing activated, runtime unchanged. Key separation itself is a real improvement and becomes the recommended trace recipe for any future trace experiment (cfg `guard_distinct`, `guard_vocab`, `guard_scope='last_user'`). Next lever is the **value quality on paraphrases** (wrong values when the own slot fires), not firing: e.g. paraphrase contexts during key writing, or a held-out paraphrase verification before dedupe.

## Evidence and limits

`report.json.gz` (every answer + native firing record + fired memory ids, binding with binary/library/model/trace/corpus/script hashes), `trace-{v1,fix}.json` (training metrics, torch eval: fix learned 100 %, v1 95 %, no probe forgotten), `trace-*.bin.items.json` (slot → memory map), `run.log`; v3b in `v3b/` (`report.json.gz`, `run.log`). Server logs and trace `.bin` files only in the project folder. A first start was killed by a container restart during trace training, before any answer (log kept in the project folder, not counted).

Claim limits: Linux x86_64 cloud CPU, not Redmi; invented facts with lexical answer keys; one greedy answer per question; trace holds 20 facts; guard_vocab = the 40 corpus questions (= the exact store); diagnosis of section 1 is post-hoc on v1 data, the fix measurement is preregistered.
