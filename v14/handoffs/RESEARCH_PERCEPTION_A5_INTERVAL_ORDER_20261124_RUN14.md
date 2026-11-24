# Research & Perception handoff — A5 interval ordering and SigLIP 2 review

**Run:** 2026-11-24, started 17:28:27 UTC; implementation checkpoint after the exact-head CI completed.  
**Release-development HEAD read at start:** `gpt6/v13-private-remote-bridge-20261111` = `8d93236c753f0194224c19edc7411d8d7082b1d6`.  
**Working stack:** Perception #2463 → this PR #2469. This branch is not the release branch.

## 1. Runtime change

The A5 temporal registry previously checked only that `end_ms` advanced. That admitted a reordered interval whose end was later but whose start moved backwards, e.g. previous `[100,166]`, next `[90,199]`. Such a frame can corrupt temporal change attribution even though the end-time check passes.

Changed `v13/code/v13/vision_temporal_evidence.py` to:
- retain the last accepted `start_ms` alongside `end_ms`;
- reject a later interval when its start moves backwards;
- clear the start baseline on reset/gap reset;
- update both timestamps only after an accepted observation.

Equal starts remain allowed for overlapping/cumulative observation windows. A rejected interval does not replace the previous valid baseline.

Added `test_temporal_visual_evidence_rejects_backward_start_when_end_advances` to `v13/code/tests/test_vision_ui_frame_ingress.py`. It checks the old false-acceptance case, the overlapping-window allowance, rejection, and baseline retention.

## 2. Exact code and evidence

- Branch: `research-perception/v14-ui-session-temporal-20261124-run11`
- PR: [#2469](https://github.com/RedMentos/Aii/pull/2469)
- Code commit: `b09f731224f71da0fdb19e81f511540329b6c2cf`
- Regression-test commit / exact code-test head: `9844efaf66c13b1e5562397ae1bc62ed7926c862`
- GitHub readback confirmed the new state field, monotonic-start guard and regression test on the branch. Subsequent handoff/ledger/Next Action/board commits are documentation-only; the exact current branch head is the live PR #2469 head, not the CI-tested code SHA.

**LOCAL_LINUX**
- CPython 3.13.5 minimal timestamp-order reproduction: PASS, 4 assertions. This is a focused invariant reproduction, not the full repository source/test suite.
- Full Aii checkout / exact project pytest: BLOCKED / NOT_RUN. No repository checkout is mounted and `git ls-remote` fails because this environment cannot resolve `github.com`.

**Exact-head GitHub Actions on `9844efaf66c13b1e5562397ae1bc62ed7926c862`**
- `frame-ingress`: PASS, 52 tests on Python 3.13 and 52 on Python 3.14.
- `vision-source-lineage`: PASS, 39 tests on Python 3.13 and 39 on Python 3.14.
- `offline-bridge-security`: PASS.
- `a5-ui-lease`: FAIL on Python 3.13 and 3.14, 17 passed / 1 failed / 5 subtests passed. The failure is the known downstream source-lifecycle composition dependency: `source_lifecycle_lock_integration_candidate.py:172` rejects `vision.py` as an unsupported lifecycle source.
- `staged-runtime`: FAIL, 19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests passed; the same `unsupported lifecycle source: vision.py` block occurs before the full staged runtime can be exercised.
- `integrated-regression`: FAIL, one setup failure from the same `vision.py` source-lifecycle block.

This is not a regression caused by the interval-ordering change. PR #2469 is intentionally stacked on Perception #2463 and does not include Core #2465. Core #2465 owns the current vision/source-lifecycle composition. Its current head `e8044b7da1c900591c1dd92211a5134a385b3b4a` advances past the vision pin but has a distinct deeper blocker: `integrated_feedback_bootstrap_candidate_20261111.py:34` reports `memory/world builder source changed`, plus a nested SHA mismatch. Do not weaken or bypass either hash check. Wait for Core/Boss to reconcile the exact dependency chain, then rebase/integrate #2469 on the accepted Core head and rerun the full matrix.

## 3. User effect and evidence boundary

The change prevents reordered A5 frame intervals from becoming false temporal deltas/novelty signals. It does **not** add a new camera provider, Android capture, native visual model, trained JEPA latent path, persistent weight learning, or a working end-to-end Android controller.

- A5 temporal consumer: code present and exact synthetic/fixture CI passing.
- Android MediaProjection/provider and real UI frame feed: NOT_VERIFIED.
- Native A3/V-JEPA inference and cross-organ learned latent exchange: NOT_VERIFIED.
- Redmi/Termux: REDMI_UNVERIFIED; no handset was connected for this run.
- Deployment: NOT_RELEASED. A GitHub push is not a device deployment. No model, weights, permissions, user data, or updater settings were changed.

## 4. Research update — SigLIP 2

Reviewed the relevant full-text sections (method, training, zero-shot/dense/localization results and conclusion) of Tschannen et al., *SigLIP 2: Multilingual Vision-Language Encoders with Improved Semantic Understanding, Localization, and Dense Features*, arXiv:2502.14786 (2025-02-20; preprint).

- ViT-B is 86M parameters; the paper also reports 303M, 400M and 1B variants. B/16 uses a 256px/256-token path in the fixed-resolution configuration. The recipe adds captioning/referring-expression pretraining, self-distillation, masked prediction and data curation; it reports improvements over SigLIP in zero-shot classification, retrieval, localization and dense features.
- The official `google-research/big_vision` codebase is Apache-2.0. The official SigLIP 2 README says software is Apache-2.0 but **all other materials are CC BY 4.0**. The Hugging Face model card metadata labels the checkpoint Apache-2.0, creating a conflict. Official issue #192, opened 2026-10-23, is still open without a maintainer clarification at this read. Treat checkpoint redistribution/derivatives as license-unclear pending clarification; do not import or ship it on the basis of the model-card badge alone.
- The training regime used up to 2048 TPU-v5e chips and 40B examples. The public implementation does not provide a verified Android/ARM64/Termux deployment path or Redmi latency/RSS. A rough FP16 parameter-only lower bound for the 86M image tower is about 172 MB, before runtime, activations and buffers; this is a calculation, not a measured file size or RAM result.
- V14 relevance: possible static A3 image-feature comparator/teacher, not a temporal JEPA replacement and not a reason to replace the existing A5 temporal path. Future test: compare its image-tower patch features against the current A3 projector and 37-value tile features on source-disjoint holdout, with a no-model baseline and downstream localization/change-attribution metrics. No download or model swap was performed.

## 5. Next executable work

1. Core/Boss: finish the #2465 source-lifecycle + nested memory/world builder pin chain without relaxing hash checks.
2. Perception/Core: once #2465 is green and accepted, rebase/integrate #2469 and rerun A5 lease, staged-runtime, integrated-regression and migration.
3. Perception's next V14-006 work after source-composer integration: near-duplicate source grouping and source-level uncertainty for A3 projector training/holdout, with exact lineage and retention controls.
4. Keep SigLIP 2 as an unadopted candidate until the weight-license conflict and a real ARM64 inference path are resolved. No user action is needed now.
