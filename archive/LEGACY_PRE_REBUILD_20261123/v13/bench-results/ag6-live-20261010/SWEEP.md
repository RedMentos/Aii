# AG6 live LoRA sweep (2026-10-10, Pakete D)
Deployed path: LFM2.5-350M Q4 C3 in llama-server b10964, master LiquidAI/LFM2.5-350M (sha 9e6c6ccf), 8 invented facts,
real job growth_consolidate -> LoraTrainer -> LlamaCppEvaluator gate. Cloud CPU, 4 threads, ~3-6 min, RSS ~2.8 GB, 20-21 steps.

| run | anchors/probes | cfg | learned | forgotten | leak | KL | gate |
|---|---|---|---|---|---|---|---|
| ag6-live-lora.json | 32/12 | bench defaults (lr 1e-3, anchor 1, all targets) | 8/8 | 1/12 | .33 | .107 | FAIL (drift, specificity, forgetting) |
| -live | 32/33 | lr 3e-4, anchor 4, all targets | 8/8 | 2/31 | 0 | .034 | FAIL (forgetting) |
| -a8 | 32/33 | + anchor 8 | 8/8 | 2/31 | 0 | .029 | FAIL (forgetting) |
| -ffn | 32/33 | anchor 4, FFN only (w1-w3) | 8/8 | 1/31 ("We live on Mars", March fact) | 0 | .028 | FAIL (forgetting) |
| -ffn2 | 48/32 | anchor 4, FFN only | 8/8 | 0 | .17 | .016 | PASS |
| -ffn2s7 | 48/32 | same, seed 7 | 8/8 | 1/30 (CO2 question) | 0 | .016 | FAIL (forgetting) |
| -ffn2a8 | 48/32 | anchor 8, FFN only | 8/8 | 0 | 0 | .014 | PASS |
| -ffn2a8s7 | 48/32 | same, seed 7 | 8/8 | 0 | 0 | .012 | PASS |

Live default now (agi/trainers.LIVE_LORA): lr 3e-4, anchor_weight 8, anchors_per_step 16, targets w1-w3.
Gate unchanged (retention delta .02 = no single flip allowed with 32 probes). Bench batches are rejected afterwards, nothing approved.
Also fixed: LlamaCppEvaluator.kl crashed (KeyError completion_probabilities) when a base answer ended with EOS before 8 tokens.
Not yet measured on the Redmi (WP-R: torch on Termux).

## WP-S5 frozen-probe drift in the gate (2026-10-10 evening)
`ag6-live-lora-drift.json`: live default, 30 frozen drift probes (specs/drift-probes.json, sha c4aa3e45…) measured on the same deployed server: KL .019 ≤ .05 → check `frozen_drift` passes, all 7 gate checks pass, PENDING_USER (then rejected by the bench). Run 535 s incl. drift probes.

## SDFT (human corrections, self-taught targets) in the AG6 batch (2026-10-10 night)
8 facts + 2 corrections ("my dog is called Bruno", "sister works as a pilot"), `--sdft`. Teacher answers by the base model with the correction in context: "Bruno", "Your sister works as a pilot." (2/2 kept). All 10 learned on the deployed path.

| run | cfg | frozen drift | KL | forgotten | leak | gate |
|---|---|---|---|---|---|---|
| -sdft | live default, full teacher answer | .053 | .015 | 1/30 (largest ocean -> "Indian") | .13 | FAIL |
| -sdft2 | live default, teacher answer cut after the key sentence | .054 | .016 | 1/30 (same) | .13 | FAIL |
| -sdfta12 | anchor 12 | .041 | .011 | 1/30 (same) | .13 | FAIL (forgetting) |
| -sdfta12s7 | anchor 12, seed 7 | .044 | .015 | 0 | .13 | PASS (learned 9/10) |
| -sdftlr2 | lr 2e-4 | .045 | .017 | 1/30 (same) | .25 | FAIL (forgetting) |
Reading: the two extra items, not target length, push drift; anchor 12 fixes drift, the ocean flip stays (same probe in every config) -> gate blocks correctly. Next: ablate which correction causes it, anchor 12 passes with seed 7 but not seed 13 (borderline), more FFN-only anchors near geography.
