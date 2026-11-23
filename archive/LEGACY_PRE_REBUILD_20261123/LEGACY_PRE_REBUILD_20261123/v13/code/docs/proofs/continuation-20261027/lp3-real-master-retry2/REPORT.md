# LP3 real-master compatibility retry 2 — 2026-10-27

Preregistered at `a5abccf47bf6581db013ac6ffad6f4638ab0564c` **before** source change `f7c52c4eee62bcee9963751359e3d47d0bc889a7` and workflow `4ff92a50c9095a20af357272c1c39cb42c87a174`. Exact parent `724df0ffbafbc984b940527dfc5c4036215c34c0`. Original native run `40523353369` remains FAIL with raw artifact `12741654668`; separate tokenizer-only metadata run `40524006855` PASS observed `BatchEncoding`, both prompts 17 tokens. This retry changes only tokenizer extraction to explicit `return_dict=True, return_tensors='pt'` and `input_ids[0]` with shape checks.

Official HF FP32 350M revision and full master SHA unchanged; one CPU frozen-base predictor/projector step, own/shift/zero controls, first-answer-token CE, frozen-base and target-free greedy checks. **Native CI pending at report creation.** No model/optimizer bytes to public artifact. On failure, preserve exact raw evidence and do not claim compatibility. Even on success this is not a utility, JEPA, Body, STEP2, B3, Age or Redmi proof. Registered negative gates and `jepa_weight=0` unchanged.

Next: read exact Actions raw result and independently verify before considering separate preregistered LP3 heldout utility cohort.


## Verified real-master result — compatibility PASS, not utility

Actions **40524404979**, exact executable SHA `4ff92a50c9095a20af357272c1c39cb42c87a174`: **SUCCESS** with pinned official full master SHA **PASS**, 15/15 focused synthetic tests PASS (3 source-only + 12 LP3 mechanism), privacy CLEAN, diff check PASS, native exit **0**. Original failed run `40523353369` remains FAIL and is not replaced.

Independently downloaded raw artifact **12743676086**, ZIP SHA256 **`67b3d44ce55d79aa3ee1da3d02e64a084d12360c32c6740f04b4bf824144c5f6`**. CRC PASS; independent receipt audit **11/11 checks PASS**; private Library raw ZIP and audit JSON uploaded and byte-for-byte readback verified. Receipt: `LP3_REAL_MASTER_COMPAT_PASS`, `LINUX_NATIVE_COMPATIBILITY`, official 350M SHA `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`, seed 73, prompt length 17, first target token only. Own↔shift answer-logit max delta **0.276328**, own↔zero **1.148773**, next-token own↔shift **0.276328**; answer CE **11.35796**, predictor gradient absolute sum **6904.86**, projector **10969.52**, frozen base gradients absent and sampled frozen tensor SHA unchanged. Target-free greedy returned the required 2 tokens. Model step elapsed **3.918 s** after load; `rss_kib_after=2,211,452` is a **post-step RSS sample, not a peak**.

This establishes **real pinned Linux FP32 C3 model compatibility with the LP3 prompt-state path and one optimizer step**, not better answers, retention, attribution of utility, JEPA/Body learning, a completed 30-step cohort, or Redmi feasibility. `jepa_weight=0`, Age authority 0; STEP2 UTILITY_FAIL, B3 L1 FAIL, BJ1 NO_SIGNAL, LP1/LP2 negative remain. **Next substantive package:** separately preregister matched CE/own/shift utility cohort with harder unseen paraphrases and leakage/drift/retention gates before any multi-step run. Independent integration review remains required.
