# Run77 — disjoint B1/B2 two-turn source-context semantic utility ablation

**Date:** 2026-10-31. **Owner:** GPT-6. **Branch:** `assistant/v13-run77-b1b2-disjoint-context-utility-20261031-auto11` from verified Run76 `98c7951720f812d7f65aee97dcfbc222cf252edc`. This is a **new seed797, six-project synthetic heldout**, not a rerun/re-score of Run52 seed479 or Run55 structural evidence.

**Registered six rows before implementation (project, max budget, max deadline, required local-only, A, B, expected action, remaining budget):**
1. Alder, 180,20,true, (160,15,true),(170,10,false) → **A,20**.
2. Birch, 200,18,true, (210,12,true),(180,16,true) → **B,20**.
3. Cedar,150,14,true,(130,16,true),(145,12,false) → **NONE,null**.
4. Dune,240,22,false,(190,20,false),(200,18,true) → **A,50**.
5. Elm,170,12,true,(160,13,true),(155,11,true) → **B,15**.
6. Fir,130,10,true,(120,9,false),(125,11,true) → **NONE,null**.

**Exact source grammar:** prior human USER event contains `Project NAME archived logistics policy. Maximum budget: X credits. Maximum deadline: Y ticks. Required local-only: true|false.`; current USER event contains `Project NAME latest logistics options. Option A: budget X credits; deadline Y ticks; local-only true|false. Option B: ... . Which option meets the archived policy? Choose A, B, or NONE and state remaining budget.` Current never repeats the policy thresholds. Each case uses fresh isolated Store/session per arm.

**Registered arms and budget:** `WITH_PRIOR` produces native B1/B2 prior offers **before** latest current USER, then native B1/B2 current offers using Run76 latest-user guard; `CURRENT_ONLY` produces native B1/B2 current offers in a fresh Store without prior. Six cases × (4+2) = **36 sequential native body calls**, no concurrent heavy jobs, max 96 observer tokens, seed797, same prompts/config across paired arms. Capture actual persisted Query/OfferPackets, source refs, raw native prompts, summaries, quotes, native metrics, release receipts, closed Store audit, no live output. No C3, no final user answer, no training.

**Frozen native pins from original Run55 evidence:** B1 LFM2.5-1.2B GGUF SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`; B2 Qwen3.5-0.8B GGUF SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`; runner SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. Model/revision/source cohort unchanged.

**Fixed strict semantic scorer before native:** a current offer is correct only if its **summary** explicitly selects the registered A/B/NONE as a recommendation/answer (not merely lists options); for A/B it must also explicitly state the exact remaining budget as `remaining ... N` or `N ... remaining`. NONE requires an explicit `NONE`/neither/no option qualifies and no invented remaining numeric value. B1/B2 each scored separately, no generous paraphrase changes after seeing outputs. Primary paired hypothesis: for **both** B1 and B2, WITH_PRIOR strict score ≥3/6 and improves over CURRENT_ONLY by ≥2/6. Secondary: at least 3/6 B2 WITH_PRIOR current OfferPackets contain a verified evidence ref into the archived policy source; query-context source transport counted separately and **not** semantic truth. If not met, scientific RED. All structural failures separate RED. No STEP2 promotion from six cases.

**Evidence:** software fixture/scorer tests first, then pinned native workflow with independent verifier, original raw ZIP, CRC/all inner hashes and private Library backup. Do not hide negative results, retune prompts or change cohort after native. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, jepa_weight=0, Redmi unmeasured, full-suite 4 FAIL/66 ERROR/28 SKIP and whole V13 incomplete. **Next:** implement and verify, serialized native launch only if software green. **Remaining platform budget:** UNKNOWN.
