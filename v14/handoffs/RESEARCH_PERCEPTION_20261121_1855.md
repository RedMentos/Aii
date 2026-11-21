# Research & Perception handoff — 2026-11-21 18:55 CET

## PR and branch readback

- Draft PR: https://github.com/RedMentos/Aii/pull/2243
- PR was opened at head 8732a395058745b8c9fdbee7d4e8d0e4b241abcb; subsequent handoff/board refresh commits are part of the same draft PR. Final head is reported in the chat after readback.

## Branch and scope

- Repository: RedMentos/Aii
- Branch: research-perception/v14-dense-latent-kv-toy-20261121
- Base at branch creation: e788dcf0b82849f4de7df229978aa9973d845093 (latest shared development branch HEAD at read time)
- Last code-bearing experiment file commit: c5fc51e876847fd075ed5b3a51a5c838c18c2e45
- Shared V14 ticket updates: V14-003 and V14-006 proof/next-step fields; R-037 in research ledger; matching live-workplan checkpoint.
- This is a research/mechanism PR, not a production B3 integration and not a release.

## What now executes

The new folder v14/experiments/latent_cache_tiny contains two independently trained tiny decoder-only models with different geometries (sender 2×24, receiver 3×32), a directed learned K/V adapter with layer interpolation and per-head gates, two-stage adapter training, actual receiver-side cache injection, negative controls, and serialization/restart equivalence.

The sender and receiver are frozen during adapter training. Phase I reconstructs the receiver's own K/V cache from the sender cache. Phase II optimizes receiver task loss while the receiver receives only the adapted cache plus the answer marker. This is a real gradient-updated adapter and a real receiver cache consumer in the tiny PyTorch experiment.

## Exact local evidence

Environment: LOCAL_LINUX, CPython 3.13, PyTorch 2.10.0+cpu, NumPy 2.3.5. No Transformers package, no Aii checkout, no GGUF weights.

- python -m py_compile latent_cache_tiny.py test_latent_cache_tiny.py — PASS
- python -m unittest -v — 3/3 PASS, 9.93 s
- Full seed-13 run — 12.41 s wall; peak RSS 344,584 KiB
- Held-out K/V reconstruction MSE — 6.5134 to 0.2054
- Phase-I latent accuracy — 85.94%; final latent accuracy — 100%
- Exact receiver-context — 100%; no-message — 0%; shuffled-cache — 12.50%; random-adapter — 13.28%
- Adapter parameter delta L2 — 20.2719; max Phase-I gradient norm — 2.1451
- Save/reload max absolute receiver-logit delta — 0.0
- Additional seeds 17/29/41 each reached 100% latent accuracy; shuffled and random controls remained near chance. Exact values are in results_20261121.json.

## Research findings

R-037 reviews the full texts of:
- Chen et al., arXiv:2606.13594v2, dense latent communication with receiver-cache reconstruction plus generation training; context-aware vs context-unaware regimes; Qwen3 pairs and one Mistral→Qwen3 pair.
- Rossi et al., arXiv:2609.32046, receiver-conditioned CacheBack selection; official OSS agentcacheback/cacheback is Apache-2.0 but its main API explicitly does not support cross-model alignment.
- Piepereit et al., arXiv:2608.16347v2, abstract-only negative causal-transfer evidence: projection retrieval does not guarantee receiver-side causal effect.

CacheBack's OSS dependencies (Python ≥3.10, Torch ≥2.4, Transformers 4.57.1–<6; optional vLLM 0.11.1) and Qwen3 focus are not a drop-in for the current llama.cpp runtime. No third-party code, model weights or data were imported.

## Production compatibility gap

The current V13 pair is heterogeneous: B1 LFM2.5-1.2B and B2 Qwen3.5-0.8B. The current llama.cpp LlamaRunner exposes generation/tokenization and a separate pooled embedding purpose; its metrics explicitly report CAN_LATENT_TAP=False, CAN_LATENT_INJECT=False and CAN_TRAIN_BODY=False. Pooled embeddings are not layerwise K/V. Enlightened Space remains symbolic. Thus the toy experiment is not native B1/B2 proof and does not change B3 status.

## Next executable step

Core must expose a model-specific native K/V tap and receiver-injection seam for the existing llama.cpp/Android runner, or explicitly evaluate a reversible runner alternative without changing installed models. Once that seam and actual model weights are available in a local development environment, Research/Perception will run exact-context, no-message, symbolic, shuffled and OOD controls on the real LFM2.5↔Qwen3.5 pair, with privacy, gradient/parameter, retention, restart/rollback, RSS and TTFT evidence.

A5 UI observation remains SHADOW/isolated until Core supplies a real OS observation grant/lease. The audio producer PR #2240 is merged, but Core PR #2242 is still open and synthetic-only; no microphone or Redmi claim.

## Safety and release boundary

No model/weight download or swap, no new dependency in the app, no microphone/UI permission, no remote shell, no device update and no user-data mutation. Full local Aii suite was not available because no checkout is mounted and GitHub DNS resolution fails. CI is not local proof. Redmi installed SHA and updater consent remain unknown: REDMI_UNVERIFIED / NOT_RELEASED. No user action is needed.
