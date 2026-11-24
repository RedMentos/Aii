# Run13P — original Linux-native CE/contrastive gradient result (2026-10-30)

Review-only; child PR #1307. Frozen prereg before code at `7528741a6a5b7a35ddec721a0baa99c611394ce9`. Original software preflight Actions `41091771052` GREEN 12/12 tests, 9/9 stage exits, original ZIP `89852143dbfeeb91f023b4072e140634136eb71c2f4f0f220cd78bd60d4685be`, 23/23 inner hashes. Native source-trigger `031abf9cfd3a3ec08f69776eec12641eed54a44f` on pinned master and new disjoint seed257; original Actions `41092009944` **SUCCESS**, artifact `12994068020` SHA256 `3ab7acab16bd4329b4bca08756a8b76c1960b7aa2261f85c011c96af17e0cefc` (11028 bytes). One download attempt failed transiently (connection reset); second succeeded, failed attempt not hidden.

## Independent original ZIP review

Original ZIP CRC PASS, 31/31 inner `SHA256SUMS` PASS, unique safe names, exact HEAD and all seven source/test/prereg Git blobs matched, **11/11 stage exits 0** (source, venv, Torch, deps, pip, software, compile, download, native, privacy, diff). Independent stdlib read-only replay validated report schema, master/revision/license/fixture SHA, source pins, zero authority and no export, frozen tensor digest equality, finite nonzero LoRA/predictor gradients, signed cosine range and weighted-ratio arithmetic. No independent second execution of model gradients is claimed.

| Measured on pinned LFM2.5-350M at one initial step | Value |
| --- | ---: |
| CE LoRA gradient L2 | 13.96694938 |
| Correct-pair contrastive LoRA gradient L2 | 1.16539654 |
| Shuffled-pair contrastive LoRA gradient L2 | 1.40751493 |
| Contrastive predictor gradient L2 | 1.91928401 |
| **0.25-weighted contrastive / CE LoRA norm** | **0.02085990 (~2.09%)** |
| CE vs correct contrastive signed gradient cosine | **+0.01273612** |
| Correct vs shuffled signed gradient cosine | -0.09408752 |
| Correct-pair contrastive loss | 1.53904057 |
| Shuffled contrastive loss | 1.34791327 |
| Frozen base tensor count | 354483968 |
| LoRA / predictor trainable parameter counts | 540672 / 1049600 |
| Optimizer steps / EMA updates / model exports | 0 / 0 / 0 |

**Interpretation bounded to this synthetic first-step probe:** both objectives produce nonzero adapter gradients, but at the candidate training weight the JEPA gradient is only about **2.09% of CE's L2 norm** and nearly orthogonal (cosine ≈0.013). This is a plausible *mechanism-level* reason the earlier Run12C 12-arm contrastive pilot had no attributable heldout NLL gain (0/3 seed wins), **not** proof of causality, no multi-step attribution, no generalization improvement and no permission to retune weight without a new preregistered cohort. The shuffled control loss being lower than the correct-pair loss at initialization is not a favorable learning result.

Private original raw ZIP saved to `/V13-Checkpoints/2026-10-30/Run13P-BJEPA-Gradient/run13p-native-original-41092009944.zip`; re-materialized and byte-compared with original **identical**. Preflight ZIP likewise byte-identical. Public repo contains only metadata, code and synthetic fixture.

**Gates unchanged:** Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, runtime jepa_weight0, no Redmi evidence, no native B1/B2 learning utility, whole system incomplete. No active learning, no model export, no user-facing output authority.

**Next independent work:** design and preregister a new multi-step CE/JEPA gradient-scaling and heldout-retention comparison only after reviewing these measurements; preserve original Run12C negative evidence and use disjoint seeds. In parallel continue canonical ContextOS/JEF/Body integration, without changing frozen runtime or ongoing owner branches.