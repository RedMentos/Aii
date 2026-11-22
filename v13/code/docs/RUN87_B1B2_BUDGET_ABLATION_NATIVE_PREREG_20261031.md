# Run87 prereg — disjoint B1/B2 observer summary-budget ablation seed877 (2026-10-31)

Owner GPT-6, isolated review-only branch `assistant/v13-run87-b1b2-budget-ablation-seed877-20261031-gpt6`, parent Run84 PR #1444 exact `7f5875e46036dd1278303dd74461a7bb6dfc24da`. This prereg is committed **before** new fixture/scorer/native execution. No overwrite of active Run85, frozen Run77 seed797, Run83 seed839, Run75 seed773, Run70 or Run11. Original Run77 scientific and independent verifier REDs remain.

**Motivation and research question:** Run77 original 36 native B1/B2 summaries all saturated a 48-character JSON schema cap, with strict 0/6 scores for each role/arm. Frozen `v13.cognition.offer_schema` computes summary cap 48 at `observer_tokens=96` and `offer_quote_min_chars=80`, cap 84 at 160. Does increasing ONLY the observer output token budget to 160, while preserving exact model, prompts, quote-minimum, source/context and strict scorer, improve paired B1/B2 semantic decisions? This is a **new disjoint** small synthetic Linux-native study, not causal proof from old data. The 160-token arm may still fail. No oracle answers in model input.

**Frozen new cohort:** seed **877**. Six projects Quartz, Rowan, Sable, Tundra, Umber, Vesper; two USER turns each: archived logistics policy ONLY in prior USER source; latest options and query ONLY in current USER source. Exact literal TABLE:

```python
TABLE = (
    ("Quartz",230,18,True,(200,16,True),(210,15,False),"A",30),
    ("Rowan",210,16,True,(215,12,True),(195,14,True),"B",15),
    ("Sable",160,13,True,(150,15,True),(155,12,False),"NONE",None),
    ("Tundra",260,24,False,(215,22,False),(230,20,True),"A",45),
    ("Umber",190,19,True,(180,21,True),(175,17,True),"B",15),
    ("Vesper",140,11,True,(130,10,False),(145,10,True),"NONE",None),
)
```

Canonical TABLE JSON (sort_keys=True,separators=(',',':')) SHA256 **`6466f5c146495209241e0ee1abf911b708774d00109383fd3c8f1fc48e27f39d`**. Oracle selects cheapest budget-eligible, deadline-eligible, required-local-only option; tie-break by deadline then A/B; balanced A/B/NONE/A/B/NONE, remaining 30/15/None/45/15/None. Source grammar exactly Run77 `prior` and `current` templates but with these disjoint projects/numbers; no policy threshold leak in current source.

**Paired arms:** SHORT_96 and LONG_160, both WITH_PRIOR, both real B1_DETAIL and B2_GIST. For each project, run both arms in counterbalanced order (even indices SHORT first, odd LONG first); isolated home/Store per arm; prior event + B1/B2 prior offers, current event + B1/B2 current offers. Exactly **6 × 2 × 4 = 48** serialized native body calls. Same `LatestUserOfferConsumer`, frozen Run52 OVERRIDES including `offer_quote_min_chars=80`, `body_question_scope=rule_decision`, `offer_style=solve`; only `observer_tokens` changes 96 vs160. Seed877, temperature0, exact original model/runner revisions: B1 LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, B2 Qwen3.5-0.8B-Q4_0.gguf SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`, llama-server SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. Licenses unchanged: LFM Open License 1.0, Qwen Apache-2.0.

**Frozen scoring:** Use Run77 `strict_summary(summary, action, remaining)` exactly, without posthoc reinterpretation. Each role per arm 0..6. Diagnostic `BUDGET_LONG_SMALL_SIGNAL_SHADOW` only if BOTH B1 and B2 LONG>=3 and LONG−SHORT>=2 AND B2 LONG verified prior evidence >=3; else `BUDGET_NONINFERIOR_SHADOW` if both LONG>=SHORT, otherwise `BUDGET_UTILITY_RED`. A structural failure remains `STRUCTURAL_RED`, retain all failed attempts and original rows. Summary cap and saturation rate are secondary diagnostics; a longer cap alone is not semantic utility. This design isolates budget in WITH_PRIOR arms, **does not prove the causal value of prior context** (no CURRENT_ONLY arm) or full system utility. No claim of independent reasoning or STEP2 promotion even if small signal appears.

**Containment/acceptance:** native FINAL/actual_model/pin, all 48 calls, process release, closed SQLite, original source/quote refs and source hashes, prompt/output hashes, no output/actions/TTY/tools/learning, independent verifier, raw ZIP SHA256SUMS and private byte-verified backup. Linux-native only, no Redmi measurement. Serialized heavy concurrency, no parallel native while Run85 owner active. First implement fixture and software-only adversarial tests; native workflow must NOT be launched until owner release and explicit source/model/seed hashes verified. No paid provisioning.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight0; Redmi UNMEASURED; whole V13 incomplete. Historical Run70/Run77/full-suite REDs retained. Remaining execution budget UNKNOWN.
