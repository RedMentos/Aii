# Independent BP1 V2 native train-proof contract review — RED/GREEN (2026-10-27)

**Owner:** GPT-6 independent review, branch `codex/gpt6-bp1-lora-proof-contract-review-20261027`, exact parent `f6d6812a493cc7d2235e97bf16e0324242d1ecd6` (owner's active LoRA V2 chain). Review-only, no main merge, no production activation.

**Concrete bug and fix:** A SHA-bound synthetic native training proof could claim rank99, wrong LoRA target, nonzero anchor weight, resumed training, wrong training base, nonfinite CE, or zero/malformed exported tensor metadata and still pass `verify_train_proof`. Added 11 independent mutation counterexamples, then fail-closed checks for actual frozen 2-step optimizer metrics/history and GGUF/PEFT export metadata. Updated existing V2 positive fixture to match fields emitted by the pinned `LoraTrainer.fit` and `run632` export verifier. Does not change the real native trainer, model/source/seed hashes, learning authority, or original scorer behavior. A declared proof remains **not independent native evidence**.

**Original software RED:** Actions `40477987654`, source `e25edc1179f26ac429a4c3c57c7097fe9c7ca2b1`, original artifact `12720604558`, ZIP SHA256 `75f9863e26f3824493aa9c121fd04ceef920250ba0f94f15fe726f402ec99d0a`; 39 tests, **11 FAIL** as prospectively expected, compile exit0, privacy CLEAN. Original ZIP CRC/HEAD/exit checked and privately backed up byte-identical.

**Software GREEN:** Actions `40478151148`, source `8adc788e204bebcf4c3df279dc08a7967fe35d25`, original artifact `12721073712`, ZIP SHA256 `2b382ff538e4dd4b8ee1501fe8d7ef47fc2855b6fa09806bdeb718e6267b9b87`; **39/39 PASS**, compile exit0, privacy CLEAN. Original ZIP CRC/HEAD/exit checked and privately backed up byte-identical. Private Library destination: `/V13-Checkpoints/2026-10-27/BP1-QAD-Proof-Contract-Review/`. No public private data or model weights.

**Separate genuine native train RED discovered during review:** Actions `40476209086` at original train source `18130b4b663705aed167fcf7b052a6eb6e38831e` ended **FAIL** after real optimizer path reached `LoraTrainer._export`: `v13.common.Unavailable: Unbekannte GGUF-Architektur: lfm2`. The isolated `gguf==0.16.3` dependency lacks the `lfm2` writer architecture; **no GGUF adapter exported, no native train proof accepted, no heldout run**. The pinned llama.cpp b10964 source tag resolves to `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` and its `gguf-py` constants include LFM2, but compatibility and mapping have **not** yet been executed. Preserve the original failure, do not claim completed training.

**Negative gates unchanged:** STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi unmeasured, full V13 incomplete.

**Next:** source-pin a compatible isolated GGUF writer, prove LFM2 tensor-name mapping and adapter export with a small no-model software preflight, then separately run serialized 25-row native training and audit original raw ZIP/adapter hash. Only afterward can source-disjoint 44-response V2 native heldout collection, retention and near-miss proceed. No forced merge, no other-owner overwrite.

Software command: `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python3 -m unittest -v tests.test_bp1_qad_lora_proof_contract tests.test_bp1_qad_lora_eval tests.test_bp1_paired_score tests.test_bp1_native_collect`.
