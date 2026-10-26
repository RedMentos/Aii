# Run628 prereg — actual CPU C3 LoRA update on pinned public master

2026-10-27 UTC. Parent Run627 PR622 head `8f3209070865ac6e3270b68ca01346fd01d17a75`. Synthetic train/heldout `COHORT.json` blob `7bf74a8b9de4f7765005093e4cb758da00b9ec0b` committed **before** script and experiment. Exclusive files: new Run628 script, tests, workflow and scoped proof. No modifications to registered Run614/618 native cohorts, prior model/seed hashes, Canon, runtime training authority or other owner files.

## Primary source and licensing

Official Hugging Face `HuggingFaceTB/SmolLM2-135M-Instruct`, exact immutable revision `12fd25f77366fa6b3b4b768ec3050bf629380bac`, Apache-2.0 license; `model.safetensors` SHA256 `5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c` (official blob page). Model is a **C3 reference master** (135M dense), not the current deployed C3 GGUF and not B1/B2. Download only from official pinned repository; verify SHA before any model load, preserve source manifest and license.

## Precommitted experiment and fail conditions

- Run existing `v13.lora_trainer.LoraTrainer` on the **actual pinned HF master** with CPU PyTorch and PEFT, exactly two synthetic fictional facts in train and two disjoint heldout prompts; frozen config in cohort (LoRA rank 2 on q_proj/v_proj, 2 steps, jepa_weight=0, no anchors). No personal data or teacher APIs.
- Measure actual nonzero trainable adapter parameter update, finite cross-entropy and heldout master KL, model SHA, generated GGUF/PEFT adapter hashes, wall time and peak RSS. Do **not** demand synthetic heldout answer improvement from two steps; report accuracy/retention honestly, including negative results. Training success is not deployed-path or Body-JEPA proof.
- Independent negative controls: tampered cohort/model SHA rejected before training; no source/master mix-up; no train/heldout overlap. Tests must be meaningful and distinct from training result. Never fake native training if dependencies/model unavailable.
- Serialize native training as one CI job with bounded time and isolated pinned dependencies, capture raw stdout/stderr, all exits, adapter/manifest hashes, privacy and SHA-closed artifacts. If download/deps fail, preserve exact failure and continue another canonical package.
- No automatic runtime import, activation, Age advancement, learning approval or native B1/B2 claim. Original gates STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi UNMEASURED, V13 INCOMPLETE.

A passing tiny C3 LoRA experiment would be **Linux-native C3 master/adaptor evidence only**, not full V13 acceptance or deployed C3 learning.
