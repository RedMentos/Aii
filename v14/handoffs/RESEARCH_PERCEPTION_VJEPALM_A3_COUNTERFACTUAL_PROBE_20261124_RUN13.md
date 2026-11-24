# Research & Perception — V-JEPA-LM / A3 counterfactual probe (2026-11-24, run 13)

## Why this work exists

The current A3 RAW EYE implementation is a single-image feature/projector path. A5's temporal RAW EYE path currently emits deterministic luminance/appearance/structure deltas and attention novelty; it is not a predictive spatiotemporal encoder. V-JEPA-LM reports that predictive encoders can carry a shared temporal-change component which a caption/QA-trained language model may fail to read unless supervision explicitly requires the change. We should measure whether the existing A3 representation has such a component before proposing a new bridge, importing a video model, or changing any installed model.

## Primary research — full text reviewed

Keuntae Kim, Dongjun Kim, Yong Suk Choi, “V-JEPA-LM: Video-Language Models That Read Dynamics Beyond Static, Text-Aligned Representations,” arXiv:2611.17831v1, submitted 13 November 2026. This is a preprint; no peer-reviewed venue was established in this review. Full 29-page paper inspected: https://arxiv.org/abs/2611.17831 and https://arxiv.cnoctave.top/pdf/2611.17831 .

The method uses a frozen V-JEPA 2.1 encoder and a trainable bridge/LLM. It studies aligned original/transformed clips using common content c=(z+z_T)/2 and change d=(z-z_T)/2. Counterfactual examples ask the same question about a clip and a transformed copy whose answer changes by construction. The paper reports:
- On held-out speed-ratio items, frozen V-JEPA features are linearly readable at 86.7%, while a caption+QA VLM answers at 33.7% (chance); the counterfactual-supervised VLM answers at 92.8%.
- At a matched training budget, counterfactual supervision adds 4.5 points on average and 38 points on natural speed questions.
- The study uses 32 frames, 1,024 visual tokens per clip, 4.53M public training samples and 1B–8B language models. It includes 14 constructions across six families.
- The paper explicitly scopes to short clips; it does not target image QA/OCR or hour-long video memory.

These are author-reported results from the preprint, not independent replication and not V14/Redmi measurements. The theory assumes transform symmetries and, for the clean cancellation argument, an appropriately shared readout; it does not imply that arbitrary A3 features contain the same subspace.

## OSS, license and device fit

Official code repository inspected: https://github.com/kkt94/Llama-V-JEPA-LM, README blob 192c206bceeeb57228c6a4f1c0b3bda1e869b910. Repository LICENSE is Apache-2.0. README states: code and bridge weights Apache-2.0; unchanged V-JEPA 2.1 encoder MIT; Qwen3 language weights Apache-2.0; Llama weights under the Llama 3.x Community License. Training data retain their own terms and several restrict commercial use; the released combined weights are described as research/non-commercial. Do not treat the combined weights as unrestricted production assets.

The smallest paper model is 1.55B total parameters (Llama 3.2 1B plus V-JEPA 2.1 ViT-L). The paper reports 13.9 TFLOPs for the ViT-L encoder on a 32-frame clip; the larger ViT-g is 37.8 TFLOPs. The repository requirements pin Python 3.12.3-era CUDA 13.0 PyTorch 2.13.0, Transformers 5.10.4 and eva-decord. No Android/ARM ABI or Redmi inference measurement was found. This is not a candidate for automatic phone installation or model swap.

## Code added

- v14/experiments/vision_counterfactual_probe.py
  - Accepts aligned [clips,tokens,dimensions] features, ±1 answer signs and source-group IDs.
  - Computes common/change components, relative change energy r_d, top-k content overlap rho, shared-direction consistency kappa, and source-disjoint change/content linear probes plus a small-sample prototype.
  - audit_a3_projector() calls an arbitrary frame projector, so it can directly audit the existing v13.vision.Projector without copying or replacing A3.
  - It stores no raw frames, feature arrays or fitted probe weights. All results are DIAGNOSTIC_ONLY.
- probe_vision_counterfactual.py: six synthetic controls for shared-change recovery, aligned framewise-reversal zero-change, shuffled-label negative control, group separation, projector subspace removal and malformed/non-finite inputs.
- probe_a3_projector_integration.py: imports the actual repository v13.vision.Projector and verifies the audit detects a deliberately removed feature direction.
- .github/workflows/v14-vision-counterfactual-probe.yml: Python 3.13/3.14 compile and test matrix.

This is an executable research diagnostic, not a production Runtime feature, not a V-JEPA implementation, not trained latent coupling and not a persistent weight update.

## Exact local evidence

Environment: LOCAL_LINUX, CPython 3.13.5, NumPy 2.3.5.
- py_compile of the probe and both test files: PASS.
- python -m unittest -v probe_vision_counterfactual: 6/6 PASS.
- Positive synthetic control: kappa > 0.90 and change-probe accuracy > 0.95; content probe remains below 0.70.
- Aligned framewise-reversal negative control: r_d < 1e-10 and kappa = 0.
- Shuffled-label negative control: kappa < 0.03 and change-probe accuracy < 0.70.
- Synthetic projector ablation removes the planted change direction and drives output kappa below 0.03.

The full repository checkout is unavailable in this runner (GitHub DNS/checkout path is not available), so the integration test importing the real v13.vision.Projector was not run locally. It is included in the exact-head GitHub Actions matrix. No full Aii suite, native model inference, Android build, Redmi test, actual A3 video-feature audit, model download, weight update, permission change or device deployment was performed.

## Next executable step

After the A3/vision source-lifecycle integration blocker is resolved and an authorized frame sequence is available, call audit_a3_projector() with the actual source-disjoint A3 frame features and transformed pairs (reversal, mirror and controlled speed change). Keep the inverse token permutation explicit. Report input-vs-A3 kappa/r_d/rho and held-out source-group accuracy. Only if the actual encoder has a measurable shared change direction and the A3 projector preserves it should the team prototype counterfactual training for a downstream temporal receiver. Otherwise keep V-JEPA-LM as an offline research/teacher candidate and do not import its weights.

## Integration and release boundary

Stacked research PR targets the current Perception session-atomicity PR #2469 branch. It does not modify runtime consumers, release branches, shared board/Next Action or installed device state. It remains NOT_RELEASED and requires independent review; whole-system issue #1984 remains the product acceptance epic. No user action is required.
