# Run339 preregistration — fresh C3 contrastive near-miss abstention vs answer-only and replay

2026-10-25 UTC. Owner: isolated Run339 synthetic C3 native experiment (new script, new fixed cohort, tests, new workflow, evidence only), parent Run338 PR #334 exact head `1ca0d552206527df10972c69e28a5f72c97c10c8`. Do not edit the original Run320/334/336 cohorts, Run334/336 native scripts/workflows, model/source/seed hashes, Canon, Age/learning/approval gates or any production model. Do not publish weights.

## Evidence driving this **new** hypothesis (not retrospective relabeling)

Run336 exact-head native CI 40219433906 SUCCESS (original three arms, strict 4-selected/144-unselected tensor audit, independent raw-score audit, raw artifact SHA256 `16115f3cdc10fb00126719d9d12b67fd921525edbb186c6dedb3e2ff23ca04dc`, 47/47 hashes independently verified). But **no utility arm passed**: all-token A 0/8 facts; answer-only B 3/8 facts, 2/6 paraphrases, near-miss leakage 0.4→0.6, forgetting 0→2; answer+replay C 3/8 facts, 3/6 paraphrases, leakage 0.4→0.6, forgetting 0→4. Original Run334 RED preserved. This is evidence of limited synthetic learning and dangerous near-miss leakage, not successful C3 learning.

## Frozen independent Run339 cohort and thresholds

New, source-disjoint synthetic invented entities, **not** Run320/Run334 and never a production truth source: `RUN339_FRESH_CONTRASTIVE_COHORT.json`, exact SHA256 `68c872c9666da20ef7e4f6c7fa6212fd859768948d1b4b3554eb46ff1684d731`, seed **53**, 8 train facts, 6 heldout paraphrases, 5 heldout near-miss questions with **explicit abstention training targets only in contrastive arms**, and frozen 12 disjoint original retention probes. No train/eval overlap of the near-miss question in the baseline comparator; D/E intentionally train near-miss abstention and their near-miss success is therefore *trained-set behavior*, not unseen generalization. Label this limitation explicitly.

Exact model/source pins unchanged: `LiquidAI/LFM2.5-350M` HF revision `9e6c6ccf47cd318696e137d381a7ded8fe4df09f`, FP32 GGUF master SHA256 `5d200c19f13483e66b39d9feb3353032581882f3eb10cc8752f027d4688d6e6f`, official llama.cpp b10964 tar SHA256 `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe`, LFM Open License v1.0. Exactly four late FFN-down tensors trainable; all other 144 unchanged required. No model artifact output published.

Three frozen arms, all seed53, 12 repetitions, 2 epochs, AdamW learning rate 1e-5, context/batch/ubatch256, threads4:
- `A_ANSWER_FACTS_ONLY`: 8 facts, answer-only, no replay (Run336 B recipe comparator on new cohort).
- `B_ANSWER_FACTS_NEGATIVE`: 8 facts + 5 explicit near-miss `I do not know ...` targets, answer-only, no replay.
- `C_ANSWER_FACTS_NEGATIVE_REPLAY`: same contrastive rows plus one of six frozen baseline self-replay anchors per repetition.

Frozen per-epoch selection: facts first-sentence key **>=4/8**, heldout paraphrases **>=2/6**, near-miss key leak **<=0.2**, near-miss first-sentence abstention **>=3/5**, zero forgotten *baseline-correct* retention probes, zero invalid outputs. Earliest passing epoch candidate-only; never activate. Conservative abstention prefix vocabulary preregistered: `i do not know`, `i don't know`, `unknown`, `not specified`, `cannot determine`, `i cannot determine`. Keep original Run334/336 thresholds and negative results unchanged.

## Verification and controls

Source-only cohort SHA/ID/denominator/answer-key/negative-key checks, deterministic training streams and marker counts, replay frequency, three-arm selection negative tests, source/model provenance, original gates. Exact-head serialized Linux-native CI only after Run338 full-suite: pinned official reader path, all three real two-epoch arms, strict GGUF selected-only tensor bytes, raw train/eval receipts, independent raw-score audit, privacy and closed artifact hashes. If any prerequisite or model run fails, record RED; do not reinterpret partial output as PASS. Even PASS would establish only synthetic trained-set near-miss abstention and heldout paraphrase/probe results, not generalized epistemic uncertainty, Body-JEPA, STEP2, B3, Redmi, AG6 or V13.

Next command after prereg: implement and run source-only tests, native serialized workflow, independently verify full raw artifact and persist source/BUILD_STATE/failed attempts. No rejected anyone-writable Drive destination.
