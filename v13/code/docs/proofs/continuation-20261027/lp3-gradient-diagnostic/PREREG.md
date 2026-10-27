# LP3 real-master missing-gradient diagnosis — preregistration 2026-10-27

New **diagnostic-only** cohort, separate from failed heldout pilot PR #734, exact parent `afbc0818b1080c11ac78cca3df5eeb6cd7b081b4`. Original Actions `40527420680` failed `Missing predictor/projector gradient` (native exit 1) before completing 24 steps; raw ZIP SHA256 `3fc467c37f92b2fe442b440c60904e626fc1ef513b92345b6c3a3d8768581004` is preserved and privately backed up. **Do not amend/replay its original registered cohort or infer utility.**

## Fixed experiment

- Official `LiquidAI/LFM2.5-350M`, revision `120bf032c36dd1273de754669da040dba7ad4982`, full FP32 `model.safetensors` SHA256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`, LFM Open License 1.0. Same isolated CPU torch 2.14.1, transformers 5.20.2, huggingface_hub 2.3.0; seed **109**, prefix_tokens **2**, no quantization.
- Measure **without optimizer updates** on each of the six preregistered training questions/answers in original order: `What is the registry marker for {cobalt,amber,quartz,jade,indigo,silver}?` with target `' '+{marigold,harbor,cinnamon,lighthouse,orchard,tundra}`. Also two original compatibility smoke questions `What is the name of my cat?`→`Brombeer`, `What is the name of my dog?`→`Tromso` from prior native compatibility PR #731, as positive-path comparators.
- For each of eight **single-row** prompts, separately measure full-answer and first-token-only CE, prompt/answer token lengths, predictor and projector absolute gradient sums, `own` versus `zero` next-token logit max delta, finite gradients and frozen base. Also evaluate the two compatibility prompts as **one two-row batch** on first target tokens to detect batch-size dependence.
- Do not optimize, alter dataset, swap model, tune hyperparameters or claim utility. Preserve raw values including zeros/NaNs and failure. Status `LP3_GRADIENT_DIAGNOSTIC_COMPLETE` means only that measurement ran; it does **not** make the failed utility cohort a success.
- One isolated GitHub Actions CPU run after software checks, native timeout 15m, job 25m; always preserve raw exit/log/result/source/prereg blob IDs, privacy/diff exits, no model/optimizer bytes. No competing heavy native owner. If diagnostic fails, preserve failure and continue other blueprint work.

## Interpretation before execution

If all six train prompts have zero prefix gradient but compatibility prompts are nonzero, suspect input-dependent causal path or tokenization; if single compatibility prompts are zero but batched positive, suspect batch dependence; if only full-answer gradients are zero, suspect target-length/CE path; if all positive, investigate optimizer-step-specific vanishing in a separately preregistered follow-up. **No automatic threshold, gate promotion or original cohort retry.** Registered LP1/LP2/BJ1/STEP2/B3 negatives, jepa_weight=0, Age authority=0, Redmi unmeasured, V13 incomplete.
