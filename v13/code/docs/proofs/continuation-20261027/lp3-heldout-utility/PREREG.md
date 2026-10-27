# LP3 real frozen-C3 heldout utility pilot — preregistration (2026-10-27)

**Frozen before implementation, dataset execution or workflow creation.** Review-only child of PR #733 exact `3fcc3f89f4b1965f6fc656744073be008eefe460`. This is a **new** independent pilot cohort; no modification or replacement of LP1/LP2/BJ1/BP2b or any registered prior run.

## Question and claim limit

Does training only the LP3 prompt-state predictor and soft-prefix projector improve **unseen paraphrase answer CE** more than a wrong-source state or zero-state prefix, with the frozen causal decoder unchanged? This is a narrow 350M Linux CPU pilot, **not** C3 deployed learning, JEPA/EMA, B1/B2, STEP2, B3, Redmi, Age or generalization beyond this tiny fixture.

## Fixed source, hyperparameters and resource envelope

- Model: official `LiquidAI/LFM2.5-350M`, revision `120bf032c36dd1273de754669da040dba7ad4982`, full FP32 `model.safetensors` SHA256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`; LFM Open License 1.0.
- Python isolated; torch `2.14.1` CPU, transformers `5.20.2`, huggingface_hub `2.3.0`; no quantization, LoRA, model replacement or external teacher.
- Seed **109**, `prefix_tokens=2`, AdamW `lr=0.005`, `weight_decay=0.0`, exactly **24** updates, six public synthetic fact pairs cycled in order four times; no target tokens in prompt-state extractor. Base model frozen/eval; no optimizer/model bytes uploaded.
- Six registry keys/answers in fixed order: `cobalt→marigold`, `amber→harbor`, `quartz→cinnamon`, `jade→lighthouse`, `indigo→orchard`, `silver→tundra`. One training question per key: `What is the registry marker for {key}?`. Two **unseen** heldout question forms per key: `Which marker belongs to {key} in the registry?` and `Tell me the registry marker assigned to {key}.`. Answers encoded as `' '+answer` (all answer tokens scored, no first-token-only shortcut).
- Wrong-source heldout control: same heldout form for the **next** key cyclically (i→i+1 modulo six), with explicit source-token extraction; no own-source row. Zero-state prefix and no-prefix frozen-base CE baselines. Frozen-model retention probes: `What is two plus two?` → ` 4`, `What color is grass?` → ` green`, `What planet do humans live on?` → ` Earth`.
- Deterministic sequential per-example scoring (avoids variable-length padding). Evaluate pre/post train and heldout own/wrong/zero CE, first-answer-token top1, and retention own CE. Verify exact full model SHA, source files, seed, training steps, nonzero finite predictor/projector gradients, frozen base parameter sample SHA pre/post.
- Reject any prompt or wrong-source text containing its target answer (casefold normalized substring), duplicated train/heldout prompts, equal source/target prompts, wrong answer mapping, invalid tokens or empty answer. No training on heldout prompts or answer-bearing source prompts. This guards explicit textual leakage but **cannot** prove absence of pretrained semantic knowledge.
- Serialize this heavy Linux-native workflow with active BP2b/native owners. Workflow max 30 minutes, native step timeout 20 minutes, CPU threads 4, record raw exit and partial failure, always upload closed raw logs/JSON, privacy scan and diff exit; no public model/optimizer weights.

## Fixed decision rule (no post-hoc threshold selection)

Record all metrics, including failure. **LP3_HELDOUT_ATTRIBUTABLE_SIGNAL** only if all are true:
1. mean heldout own CE improves by at least **0.05** from pre to post;
2. post own CE is at least **0.03** below both wrong-source and zero-state post CE;
3. own CE improvement exceeds wrong-source improvement by at least **0.03** (difference in differences);
4. post own first-token top1 count exceeds both wrong-source and zero by at least **1/12**;
5. mean retention own CE worsens by **<0.20**, and base weights/gradients unchanged;
6. all source/leakage/integrity checks pass and native exits are zero.

Any unmet condition → `LP3_HELDOUT_NO_ATTRIBUTABLE_SIGNAL` (or `INCONCLUSIVE` for execution/measurement failure). Even a pilot signal does **not** promote LP1/LP2, BJ1, STEP2, B3, `jepa_weight`, Age authority, Redmi or whole-system gates. A larger separately preregistered multi-seed real-utility cohort would still be required.

## Next exact commands

After this prereg commit is remotely verified, implement a new standalone runner and standard-library dataset tests; verify software CI. Only then launch the opt-in pinned Linux-native workflow if no competing heavy owner is running. Archive original failed attempts unchanged; independent review required before integrating.
