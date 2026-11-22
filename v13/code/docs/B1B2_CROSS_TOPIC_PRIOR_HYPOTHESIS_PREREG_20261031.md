# B1/B2 cross-topic retained hypothesis leakage prereg — 2026-10-31

Owner GPT-6, next review-only hardening package on PR #1384 after verified 95/95 software checkpoint `2a40adf4c32cd376e5a4255a116130656f4dcf98`. Preserve original raw and registered Run52 `Cognition`, fixture seed479, model/scorer/runner hashes and Canon.

Hypothesis: the frozen `Cognition.offer` reads the latest retained B1 `previous.offer.summary` and includes it as `prior_hypothesis` in the *model prompt*, even when the new causal/project filter makes `context_source_refs=[]`. A Harbor-specific summary may therefore enter a Willow prompt with no matching source provenance. This is not fixed by the previous context-only adapter.

Precommitted synthetic diagnostic: use the unchanged real Cognition with a synthetic FakeBody that emits a unique Harbor-only summary, then capture the next Willow B1 Query/runner prompt and prove the stale Harbor hypothesis is present while context source refs are empty. The new `CausalOfferConsumer` must fail shut **before** runner/Query/Offer/state writes when retained prior event has a different or ambiguous explicit project identity. Same-topic forward B1/B2 and stale replay protections remain. Do not reset or silently overwrite retained state, do not modify frozen Cognition, and do not claim that refusing cross-topic offers is a usable topic-partitioning solution. A future separately approved topic-scoped state design must allow legitimate topic switches without leakage.

Test original diagnostic + guarded no-side-effect refusal, same-topic green, restart, source revocation, 95 previous tests. CI raw preserved, pins/privacy. No native/Redmi, C5/C6 output, Age/STEP2/B3/JEPA promotion, production merge or seed479 rescore.
