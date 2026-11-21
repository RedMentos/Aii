# V13 B1/B2 role fit and Redmi timeout — 2026-11-13

## User correction, not a new hard model-size constraint

The owner clarified the original Canon intent on 2026-11-13: **B2_GIST need not always be larger than B1_DETAIL**. If otherwise similarly fitting candidates differ modestly in size, **prefer the slightly larger model on GIST**. Do not implement size as a hard capability or selection rule; correct functional specialization and measured native feasibility have priority. No model swap, download, adapter swap or source changes are authorized by this note alone.

## Binding source

Canonical architecture: `v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`.
- B-PLANE §§ B1/B2 (around lines 459–489): B1 is short-window literal/fine, exact-source, numbers/code/local differences. B2 is multi-token/event/global/discourse/plan, adaptive coarse slots **not merely a summarizer**.
- G1/G1B (around lines 6417–6435): two actual pretrained bodies, distinct resolution and source-bound cross-scale links; ~1 fine token vs ~8-token-equivalent/12 gist slots are BOOT measurements, not tokenizer rewrites.
- IH-H6 (around lines 5863–5917): actual **Redmi** runner proof before adopting a production candidate: revision/checksum, peak/steady PSS/RSS, real prompt prefill, first token, decode, thermal, cancellation and reload.
- R0/R1 (around lines 7640–7662): measure unique B1 vs B2 wins, correlated failures, exact-local/discourse/mixed tasks, source links and latency. Replace a non-complementary model pair or role adapters, not the split-brain goal.

## Current frozen test configuration (not proof of role-fit)

`v13/code/specs/models.json`: B1_DETAIL=LFM2.5-1.2B-Instruct QAD-Q4_0, B2_GIST=Qwen3.5-0.8B Q4_0, C3_LANGUAGE=LFM2.5-350M QAD-Q4_0. This size order differs from the owner's *soft preference* but is not itself a proven functional failure. It originated as a research candidate; installed phone state must be verified independently. Never infer resident RAM or live role usage from compressed GGUF file sizes.

Technical-only device evidence summarized in public issue #1872: latest B1 native probe `TIME_BUDGET` (43.1s), B2/C2/C3 probes marked OK, last foreground turn missed 30s deadline during C3 prefill after 15s JEF/observer. These do not show that swapping B1/B2 GGUFs would fix B1. Native phase attribution in PR #1869 is not released; PR failed exact-head pinned staging/owner-read CI.

## Next required implementation/testing

1. Keep the official Age 0 and the exact B1/B2 functional roles; preserve the provenance-bound source links, JEF offer channel, learning gates, negative STEP2/B3 evidence.
2. Repair/pin-compose PR #1869 CI without changing frozen sources or bypassing its source-integrity checks; separately retain smoke-generation and structured-offer phase timings even if the latter fails.
3. On Redmi, measure each body's actual source revision, load/template/prefill/offer stage, cold vs warm, peak PSS/RSS, deadline/thermal, unload/reload, selected thread/context/batch knobs, and at least one actual role-distinct exact-local, long-global and mixed source test; preserve failed cases.
4. Compare alternative B1/B2 model assignments under **equal tasks, resources and input history** (including the current assignment as baseline) before proposing a user-visible model swap. If candidates are comparably fitting, resolve close ties toward a slightly larger GIST.
5. Report two independent conditions: (a) the selected B1 actually finishes useful detail/offer inference inside the phone's budget, and (b) B2 maintains genuine cross-scale/global complementary representations. Never label a green synthetic CI result native success.

## Separate core update-safety patch on this review branch

`chat_service.py` and `lifecycle.py` guard explicit OFF against stale update-resume markers and defer explicit/manual or supervisor starts while the source update is CHECKING; `tests/test_chat_service.py` contains exact synthetic regressions. This does not alter the assigned models, inference budgets or native scheduling, nor prove B1 fixed. CI and device lifecycle review are still required.
