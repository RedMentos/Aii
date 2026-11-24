# Run117S — B2 salient exact-source retention and disjoint Body-complementarity preflight

## Canonical chain and ownership

Review-only branch `assistant/v13-run117s-b2-salient-source-shadow-20261031-hourly11` from exact `d8f5d88cf5d620c114b6b758274753321ef1e4fb` (Run117R #1498, Run117Q #1497, Run117P #1496, Run116 #1495/#1494). Owns only new candidate module, new preflight script, two tests, one **new disjoint** frozen seed1061 fixture, scoped docs/workflow. Frozen Cognition, Runtime, JEF, C3, Body, existing fixture cohorts and model/source hashes are **unchanged**. This is not production-integrated. Age0 RECORD_ONLY, no delivery/tools/learning.

## Newly observed bottleneck and candidate

Frozen B2 retained context uses `Cognition.body_context` and takes **the first 240 characters** of an earlier USER source (`excerpt_ref.char_end=min(...,+240)`). In the six new cases the **binding policy occurs after archive distractors**, so the prefix truncates a crucial rule (demonstrated by a real SQLite test). The old path can lose `local-only` or the deadline before B2 and C3 see the policy.

`v13/code/v13/b2_salient_source_excerpt_shadow_candidate.py` adds a **default-OFF** exact-source selector, not a replacement for frozen Cognition. It verifies the current/latest USER event, same session/generation/project, prior persisted B2 OfferPacket/model revision, original retained prefix SourceRef and byte-exact source, then finds **exactly one** explicit `Binding policy: budget ...; deadline ...; local-only ...` sentence in the full prior USER source. It returns an exact SourceRef window of **at most 240 chars** containing the complete policy; no oracle, option evaluation or model claim. Ambiguous/missing/stale/deleted/foreign sources fail closed. An opt-in isolated `_SalientCausalOfferConsumer` wrapper uses this context during B2 current-turn offer while retaining existing causal, topic-partitioned and analyst_context quote checks. The wrapper may invoke a Body runner and persist a SHADOW OfferPacket, but never commits output/tools/learning; native model execution is **not proven** by software tests.

This grammar-specific selector is a *deterministic source-retrieval baseline*, not a general semantic salience learner or proof of Body intelligence. It is isolated from live Runtime and has no authority to promote semantic truth. Body summaries remain hypotheses.

## New frozen cohort and three source-only arms

`docs/fixtures/RUN117S_BODY_COMPLEMENTARITY_SEED1061.json`: SHA256 `11d499eeb04d83e3786fe12046207ec3d0fc6684f5220a5fc1943202cd0f31de`, seed **1061**, six disjoint project cases **Atlas, Boreal, Cinder, Delta, Elm, Flux** with prior archive distractors, later binding policy, current options and independent deterministic oracle. Frozen oracles A/50, B/70, NONE/null, A/50, A/50, NONE/null. This is a new registered **candidate** cohort; do not overwrite its bytes or silently change seed/oracles after review.

`run117s_body_complementarity_preflight.py` constructs three C3 SYSTEM/USER-role-separated arms with **no answer injection**: `RAW_FULL_SOURCES` (two exact USER texts), `SOURCE_SPANS_ONLY` (deterministic exact policy and option spans with Store SourceRefs), `BODY_VERIFIED_QUOTES` (only B1/B2 exact verified quote spans, no raw full source or Body summary/hypothesis). Common C3 system instructions and no typed JEF oracle in any arm. This isolates Body *source selection* from the deterministic selector, unlike Run116's answer-copy test. C3 inference is **not** performed in preflight.

## Evidence and limits

On Linux/Python 3.13, six real SQLite Stores with **deliberately synthetic QuoteBody** observers: **6/6** model-free preflight PASS; B2 selected window includes the complete late policy, B1 current quote contains exact options, B2 current verified quote contains exact prior policy, all retained Query/Offer and ContextPlan-independent source checks pass, no assistant output/actions. The Body test double intentionally selects the correct numbered quote; it is **not evidence that a native B2 model can do this**. Preflight `report.json` SHA256 `485ff1935857430307da3798c946a720668bb16a64170399a93138f907497289`. New 7 selector + 4 preflight tests and inherited suites **78/78 PASS**, compile PASS, combined raw SHA256 `3bd78302b9f50255286d40a5eba439bfb79f34028a8a12f4d0132ea03aa5fd96`. All original negative gates remain RED. No new native model calls or Redmi tests.

Files, SHA256 / remote Git blob:

- Selector: `b639ea0aa0b8fee15af024c5a97fc8f13dd851038d19985fba7ce7dc412b529a` / `36d8ad62bd23e5c93b56469c2c0962f882d6a4e3`.
- Preflight script: `27ca730647686ee56922235086959ab6bde0ede43af9ec264fc74c3ee76f046d` / `2fde8a1bccefae8067947560974d7df0b0e18bfb`.
- Selector tests: `282c3cf1df23e1e83a6c9bcc83c675d943c24262b9faf4503abeace2aaeba2d6` / `ce46bec8ad8cccf551472a9080ff6f4cbd76deae`.
- Preflight tests: `64c43a1496a038c05e5b84275cb6554061c711997134c40ef2008e13aa001791` / `3d01dc477ac15e3b25e766ae6b4c1a3034de99a1`.
- Fixture: `11d499eeb04d83e3786fe12046207ec3d0fc6684f5220a5fc1943202cd0f31de` / `f7741de466571e67e48720395f32acbcb32ff14a`.

## Next exact commands and acceptance boundaries

CI: checkout exact branch HEAD, verify five Git blob hashes and frozen fixture SHA, run model-free six-case preflight with fresh work/out, 78 focused tests, compile/privacy/diff, retain raw SHA256SUMS, download original CI artifact and independently verify before review acceptance. Keep private raw checkpoint in `/V13-Checkpoints/2026-10-31/Run117S-Salience/`.

After CI: implement a **new native pilot** with the same preregistered seed1061 and pinned B1/B2/C3 models, six cases and three arms. Record original source/fixture/model hashes, process reaps, prompt hashes, native metrics and raw negative evidence; compare Body quote selection to deterministic source selector and raw full-source control. Fail closed if native B2 cannot quote the late policy. No promotion of STEP2/B3/Body-JEPA or generalization from 6/6 synthetic transport. The current candidate's hardcoded English anchor is not a general solution and may miss natural language variants.

Reproduce:

```sh
cd v13/code
PYTHONPATH=. python -m scripts.run117s_body_complementarity_preflight --fixture docs/fixtures/RUN117S_BODY_COMPLEMENTARITY_SEED1061.json --work NEW_EMPTY_WORK --out NEW_EMPTY_REPORT
PYTHONPATH=. python -m unittest -v tests.test_run117s_b2_salient_source_shadow tests.test_run117s_body_complementarity_preflight
```
