# Core & Harness handoff — exact greeting reflex Runtime slice

**Date:** 2026-11-26  
**Owner:** Core & Harness  
**PR:** #2529 — https://github.com/RedMentos/Aii/pull/2529  
**Branch:** `core/v14-greeting-fastpath-runtime-20261126-run1`  
**Exact head:** `82f3bc511529c365d96ee43b59f9451e6096465b`  
**Base:** Core #2493 branch `core/v14-runner-warm-retention-current-stack-20261125-run1` at `24815e67c75a8c58875e5f1cc3bbc0ee95d44bde`; parent chain #2490 → #2488.

## Implemented Runtime path

- Existing `v13/code/v13/greeting_fastpath.py` is now called from `Runtime._turn` after operator-authored exact output-policy rules and before arithmetic.
- It accepts only a bounded whole-text greeting from its explicit allowlist, bound to a text SourceRef. It rejects non-text or mixed modality, audio/image/video fields, control characters and oversized inputs.
- The response is stored as a source-bound `BUILTIN_GREETING_REFLEX` source, represented by the existing fixed-rule/C5 output path and committed through the normal output transaction/broker.
- Message metadata records the rule, language, scope and hashes, with `model_generated=false` and `native_models_invoked=false`.
- Non-greeting text such as “Hi, how are you?” falls through to normal Perception and the full multi-organ route. No B1/B2/C3 component was deleted or globally disabled.

## Verification

- LOCAL_LINUX isolated matcher test: **1/1 PASS**. The exact fetched matcher and test fixture Git blob hashes were checked against remote readback.
- Full local Aii checkout / Runtime pytest: **BLOCKED / NOT_RUN**. `git ls-remote` fails because this environment cannot resolve github.com; no local checkout is mounted.
- Exact-head GitHub Actions run 45763142595: **SUCCESS** on Python 3.13 and 3.14. Each version:
  - py_compile: PASS
  - runner interruption/warm-retention: 9/9 PASS
  - arithmetic fastpath regression: 22/22 PASS
  - greeting Runtime + negative fallthrough: 3/3 PASS
- Existing private-bridge workflow run 45763142633: SUCCESS, unrelated to greeting behavior.
- Runtime integration CI uses the actual Runtime/SQLite code path, while native model calls are mocked out for the greeting case. It is software integration evidence, not native model or Android latency evidence.

## Product and safety boundary

- A whole-text greeting can now receive a deterministic fixed acknowledgement without loading B1/B2/C3. This is a narrow reflex, not a general answer path and not a model-generated response.
- Longer questions and mixed-modality inputs continue through the normal route.
- No model, weights, permission, installed app, user data or device state was changed.
- TERMUX/REDMI: **REDMI_UNVERIFIED**. No phone was connected or queried. The candidate is DRAFT and NOT_RELEASED; no updater request was sent.

## Next work

1. Keep #2529 stacked until #2493 and its #2490/#2488 parent chain are reviewed and integrated.
2. After an authorized integrated release, measure greeting TTFT on Redmi cold/warm and check that the fastpath is materially faster without false matches.
3. Return to the higher-impact V14-001 gap: real B1_DETAIL + B2_GIST attempts, source-bound OfferPacket delivery, C4 selection and C3 native prefill/generation in the same nontrivial turn. A fast greeting is not a substitute for that work.
4. Preserve current native/Redmi evidence distinctions and keep B3 production OFF until its separate utility gates pass.

**User action required:** NONE. No manual Termux command, model swap or permission change is justified.
