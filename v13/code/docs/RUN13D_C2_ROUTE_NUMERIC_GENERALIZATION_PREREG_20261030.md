# Run13D — C2 route-head v1/v2 numeric-notation transfer (2026-10-30)

Prospective **synthetic software-only** learning ablation, review-only child of #1287 at `7baea8983bf4aeb7ebe24fda19b79e97b46a136c`. Owner GPT-6. This is NOT native Needle inference, human route feedback, learned route authority or a model swap. Existing `route_words.py` v1 blob `901f993ce815a1ccc10808c6d3272078d4300580` and isolated v2 `route_words_numeric_candidate.py` blob `1ba6ec6c1b2002cbc44164286404cd9d915b2cac` remain frozen.

## Frozen cohort, before code

Four synthetic class labels 0 simple / 1 detail / 2 gist / 3 both. Exact templates in class order: `half {n} please`, `quote {n} exactly`, `summarize {n} briefly`, `compare {n} conflicts`. Train numeric strings `1` through `8` in order for each class (32 rows); holdout strings `100000`, `7000000`, `3.14`, `1.23e-5`, `99,999`, `8%`, `-20`, `.5e-3` in that order per class (32 disjoint rows). Frozen SHA256 of UTF-8 `json.dumps({"train": [[text,label],...], "holdout": [[text,label],...]}, sort_keys=True, separators=(",",":"))`: **`563f530aac86a1e4ab5314d0833538ffe3587013742951e5a1cf9474a60c6140`**. No rerolling after results.

Use **the same** existing NumPy `learning_worker.train` for v1 and v2, same 32 train rows, labels, order, hyperparameters, synthetic constant embedding `[1,0,0,0]` (NOT native), same scaffold labels. No active checkpoint or old weights. Train each head in a separate temporary directory; never load v1 weights under v2. Frozen config: `learning_steps=80`, `eligibility_decay=.95`, `learning_rate=.02`, `max_update_norm=.02`, `retention_max_delta=.02`. Independently score all 32 holdout rows and train rows with matching v1/v2 word vectors and identical softmax/logits. Include per-class accuracy/confusion and a deranged-label negative-control fit. Record all outcomes even if v2 loses.

## Prospective decision and claim limits

Hypothesis: v2 numeric normalization improves held-out numeric notation generalization without harming train recognition. Exploratory signal **v2 holdout accuracy >= v1 + 0.125 (4/32)** and v2 train accuracy >= v1 train accuracy - 0.05. This is NOT a promotion gate, and failure remains failure. Required software structural controls: frozen fixture hash, feature revision separation, identical synthetic embedding and hyperparameters, finite training and deterministic checkpoint reload, 32/32 heldout rows scored, no native calls, no Store writes, no changes to original route head or weights. The deranged-label control must be reported even if unexpectedly strong; no posthoc exclusions.

CI: focused ablation and inherited route_words tests, py_compile, Canon blob, privacy/diff, closed raw and SHA256SUMS, private backup. Never claim this synthetic transfer proves human-route accuracy or actual C2/Body utility. Future required experiment: separately preregister **real explicit human labels and native C2 embeddings** with disjoint heldout, retention, latency and Redmi measurements, and only then consider approval.

Negative gates unchanged: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight0; Redmi unmeasured; V13 incomplete. Historical Run13A native utility RED and G13 fullsuite RED unchanged.
