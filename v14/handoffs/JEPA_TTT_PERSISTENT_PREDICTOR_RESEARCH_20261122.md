# JEPA-TTT research handoff — 2026-11-22

## Primary source reviewed

Zheyuan Zhang, Suyu Ye, Nakul Agarwal, Hossein Nourkhiz Mahjoub, Ehsan Moradi Pari, Daniel Khashabi, Tianmin Shu, Vaishnav Tadiparthi, **“JEPA-TTT: Persistent Test-Time Training of Latent World Models for Planning under Dynamics Shifts,”** arXiv:2610.00722, submitted 2026-09-30; accepted to the NeurIPS 2026 Workshop on World Models in Physical AI.

- Full paper HTML reviewed: https://arxiv.org/abs/2610.00722
- Authors' project page and result tables: https://jepa-ttt.github.io/
- Evidence level: FULLTEXT_REVIEWED / workshop paper; no independent reproduction in V14.
- The paper page does not link an official implementation repository. No code, weights, dataset, or dependency was imported; no software or weight license was available to adopt from the inspected project page.

## Mechanism and reported evidence

- The system updates an action-conditioned JEPA latent dynamics predictor from observed transitions. It keeps the visual encoder and reward head fixed during deployment.
- Predictor parameters, AdamW optimizer state, and replay buffer persist across episode boundaries. This persistence is isolated with a matched update-count control rather than attributing gains to more gradient steps.
- Dense replay constructs a prediction window at every valid temporal offset, stores the windows, and samples minibatches uniformly from the accumulated buffer. The paper separates extra optimization, temporal coverage, and replay under matched update budgets.
- Across eight single, persistent dynamics shifts in four continuous-control environments, the authors report mean best held-out score 0.678 versus 0.267 for frozen JEPA, mean AUC 0.571 versus 0.267, and 83% lower five-block autoregressive latent prediction MSE after 500 episodes. Three deployment runs are reported per shift.
- In the separate persistence control, retaining predictor and optimizer state raises mean best score 0.289 to 0.729 and AUC 0.273 to 0.637 at matched update count.

## Limitations that matter to V14

- The study does not evaluate returning to the original dynamics, sequences of shifts, retention, catastrophic forgetting, forward/backward transfer, or cross-organ learning.
- It updates only the predictor. This is a useful experimental arm, not a reason to make a frozen encoder/teacher the final V14 architecture.
- Its input is temporally ordered observation/action trajectories. Current trusted T8 rows are discrete source-bound state/action/outcome records; dense overlapping windows are only valid if sequence ordering and temporal adjacency can be verified. Do not synthesize adjacency from timestamps alone.
- The reported results use robotics/continuous-control benchmarks and LeWorldModel; they are not LLM/GGUF, mobile CPU, or Redmi measurements.

## Concrete V14 experiment

Keep the current full-encoder JEPA path and source-disjoint A→B→A retention gate. Add a bounded predictor-only persistent baseline as a comparison arm, not as the architecture endpoint:

1. Use only verified T8 transitions with an explicit same-session predecessor/successor relation and exact source/outcome hashes.
2. Compare chronological single-use stream, dense valid-window stream, and dense replay under equal optimizer-update and row/compute budgets.
3. Retain predictor + optimizer state across process restart; compare against matched reset control.
4. Use disjoint per-session A/B holdouts and return-to-A tests; report each session, not aggregate-only means.
5. Include no-update, shuffled-window, wrong-action, and reset-optimizer negative controls.
6. Require parameter/EMA/optimizer diffs, prediction loss and downstream B1/B2/SELF receiver utility, checkpoint SHA readback, restart, rollback, CPU/RSS and Android-specific measurements before promotion.

Current V14 implementation already has persistent numeric predictor/optimizer state, trusted T8 provenance, source-disjoint holdouts, replay selection and a predictor-only arm. The paper therefore supplies a benchmark design/control, not a dependency or a claim that current V14 meets its results.

**Decision:** RESEARCH_ONLY / NO_CODE_IMPORTED / NO_LICENSE_ADOPTED / NO_ANDROID_PROOF. Do not change the active model, weights, learning permissions, or replay policy on this basis alone.


## Independent reproduction / OSS readback

- Independent reproduction: https://github.com/ZhengQingJing/jepa-ttt-reproduction, latest inspected HEAD `30002a766ecfc133245d3260d059fea2d768f486` (2026-11-21). This is **not the authors' official implementation**.
- Repository license: MIT. Its pinned upstreams are LeWorldModel `8edfeb336732b5f3ce7b8b210d0ba370a09e2cac` (MIT) and stable-worldmodel `21446f1ede6d5284e981bd7b47f432b994e6d812` (MIT); the reproduction includes both upstream license texts.
- The reproduction README documents a CPU-only standard-library results verifier, but training/deployment uses Linux, Python 3.11, PyTorch 2.8.0+CUDA 12.6, torchvision 0.23.0+CUDA 12.6, Transformers pinned to commit `21fac7abba2a37fae86106f87fcf9974fd1e3830`, and an RTX A6000 in reported runs. Its model is ViT-Tiny/14 with 192-dimensional latents; this is not a mobile/ARM candidate.
- It provides separate result sets for Two-Room, Reacher and OGBench-Cube, persistence controls, fixed-trajectory prediction diagnostics, and dense/sparse stream controls. The README reports its own Two-Room results separately from paper reference values, which is useful evidence hygiene.
- Reuse decision: **algorithm/evaluation reference only**. MIT code is technically reusable with attribution, but its CUDA/PyTorch/robotics dependency chain and model scale are inappropriate for direct Redmi integration. No source, weights, assets, or dependencies were downloaded or imported in this run.
