# Research & Perception handoff — 2026-11-21 19:02 CET

## Latest exact-head checkpoint

- Draft PR: https://github.com/RedMentos/Aii/pull/2243
- Branch: `research-perception/v14-dense-latent-kv-toy-20261121`
- Exact branch/PR head read back: `ae26c94700ca8077b38cbd87c40db89b4ae46360`
- Previous head: `543349894b5392582969f06a4485ff9d18e4504d`
- New commit: `ae26c94700ca8077b38cbd87c40db89b4ae46360` — explicit CI reproduction of the tiny K/V experiment.
- Workflow blob readback: `9210514dee0225940bbc1219db4cd53c30de28e7`; README blob readback: `6498e6111af9ea6f6574f6246f3bb2ba4a0861b0`.
- Status: OPEN / DRAFT / NOT_RELEASED / REDMI_UNVERIFIED. GitHub currently reports mergeable=false during refresh; do not assume ready-to-merge from the successful tests alone.

## Boss-requested CI reproduction — complete

The earlier green generic `model-lab` discovery did not recurse into `latent_cache_tiny/`. The workflow now has a separate `latent-cache-tiny` job that:

1. Installs pinned test-only `numpy==2.3.5` and CPU `torch==2.10.0+cpu`.
2. Verifies both exact package versions.
3. Explicitly compiles `latent_cache_tiny.py` and `test_latent_cache_tiny.py`.
4. Runs `python -m unittest -v` with the experiment folder as working directory.

Exact PR-head checks for `ae26c94700ca8077b38cbd87c40db89b4ae46360`:
- Actions run **44938520228** — `latent-cache-tiny` PASS; existing `model-lab` PASS.
- Actions run **44938520229** — public privacy scan PASS.
- Local YAML parse/structure check on the workflow — PASS.
- The experiment code and tests themselves were unchanged by this workflow-only commit. The prior LOCAL_LINUX experiment evidence below is still tied to the same unchanged source/test blobs; the new exact-head Actions run independently executes them.
- PyTorch and NumPy are BSD-3-Clause test-only CI dependencies. They are not product/runtime dependencies. No model weights, user data or training data were downloaded.

## Final base synchronization

- The shared branch advanced after the PR was opened. This branch was brought forward with a normal two-parent merge commit onto base `b267ed641f4dbff1e2c28f492baf0182e9bb656b`; no force-push or destructive rewrite.
- The workflow/README commit was a normal fast-forward update using expected previous head `543349894b5392582969f06a4485ff9d18e4504d`.

## Branch and scope

- Repository: RedMentos/Aii
- Base branch: `gpt6/v13-private-remote-bridge-20261111`
- Last code-bearing experiment file commit: `c5fc51e876847fd075ed5b3a51a5c838c18c2e45`
- Shared V14 ticket updates: V14-003 and V14-006 proof/next-step fields; R-037 in research ledger; matching live-workplan checkpoint.
- This is a research/mechanism PR, not a production B3 integration and not a release.

## What now executes

The new folder `v14/experiments/latent_cache_tiny` contains two independently trained tiny decoder-only models with different geometries (sender 2×24, receiver 3×32), a directed learned K/V adapter with layer interpolation and per-head gates, two-stage adapter training, actual receiver-side cache injection, negative controls, and serialization/restart equivalence.

The sender and receiver are frozen during adapter training. Phase I reconstructs the receiver's own K/V cache from the sender cache. Phase II optimizes receiver task loss while the receiver receives only the adapted cache plus the answer marker. This is a real gradient-updated adapter and a real receiver cache consumer in the tiny PyTorch experiment.

## Exact local evidence

Environment: LOCAL_LINUX, CPython 3.13, PyTorch 2.10.0+cpu, NumPy 2.3.5. No Transformers package, no Aii checkout, no GGUF weights.

- `python -m py_compile latent_cache_tiny.py test_latent_cache_tiny.py` — PASS
- `python -m unittest -v` — 3/3 PASS, 9.93 s
- Full seed-13 run — 12.41 s wall; peak RSS 344,584 KiB
- Held-out K/V reconstruction MSE — 6.5134 to 0.2054
- Phase-I latent accuracy — 85.94%; final latent accuracy — 100%
- Exact receiver-context — 100%; no-message — 0%; shuffled-cache — 12.50%; random-adapter — 13.28%
- Adapter parameter delta L2 — 20.2719; max Phase-I gradient norm — 2.1451
- Save/reload max absolute receiver-logit delta — 0.0
- Additional seeds 17/29/41 each reached 100% latent accuracy; shuffled and random controls remained near chance. Exact values are in `results_20261121.json`.

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

No model/weight download or swap, no product dependency addition, no microphone/UI permission, no remote shell, no device update and no user-data mutation. Full local Aii suite was not available because no checkout is mounted and GitHub DNS resolution fails. CI is not local proof. Redmi installed SHA and updater consent remain unknown: REDMI_UNVERIFIED / NOT_RELEASED. No user action is needed.
