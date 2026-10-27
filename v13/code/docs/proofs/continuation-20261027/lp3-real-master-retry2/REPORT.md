# LP3 real-master compatibility retry 2 — 2026-10-27

Preregistered at `a5abccf47bf6581db013ac6ffad6f4638ab0564c` **before** source change `f7c52c4eee62bcee9963751359e3d47d0bc889a7` and workflow `4ff92a50c9095a20af357272c1c39cb42c87a174`. Exact parent `724df0ffbafbc984b940527dfc5c4036215c34c0`. Original native run `40523353369` remains FAIL with raw artifact `12741654668`; separate tokenizer-only metadata run `40524006855` PASS observed `BatchEncoding`, both prompts 17 tokens. This retry changes only tokenizer extraction to explicit `return_dict=True, return_tensors='pt'` and `input_ids[0]` with shape checks.

Official HF FP32 350M revision and full master SHA unchanged; one CPU frozen-base predictor/projector step, own/shift/zero controls, first-answer-token CE, frozen-base and target-free greedy checks. **Native CI pending at report creation.** No model/optimizer bytes to public artifact. On failure, preserve exact raw evidence and do not claim compatibility. Even on success this is not a utility, JEPA, Body, STEP2, B3, Age or Redmi proof. Registered negative gates and `jepa_weight=0` unchanged.

Next: read exact Actions raw result and independently verify before considering separate preregistered LP3 heldout utility cohort.
