# Research & Perception handoff — cross-architecture activation transfer

Date: 2026-11-22  
Stack base: Boss integration branch `boss/v14-run11-current-evidence-sync-20261122` at `675666c695d5d1cad7126b384db4fb0ac31d3d17`  
Branch: `research-perception/v14-r091-cross-arch-steering-20261122-run7`  
Status: RESEARCH_ONLY / NOT_RELEASED / REDMI_UNVERIFIED

## Research finding (R-091)

Full paper read: Ayushi Agarwal, *Cross-Architecture Steering Transfer in Language Models: A Systematic Empirical Study*, arXiv:2608.05164, submitted 2026-05-26; preprint, not peer-reviewed in this review.

The study evaluates five English decoder-only models across two architecture lineages, uses residual-stream mean-pooling at roughly 50% depth, TopK SAEs, MNN feature matching and a 67M-parameter MLP bridge per directed model pair. It reports 47–49% cross-model feature-pair validation at ≥1.7B and 29.9–33.3% at 0.8B. Functional vector steering reports 71.0% win rate versus 68.0% native and 65.7% zero-projection; the 3 pp native comparison is not statistically conclusive (paired t(4)=1.85, p=0.14). The 1.7B boundary is only suggestive: one model per tier below 7B, and scale is confounded with positional encoding. QA and biomedical transfer are weak. All models share a corpus, and the paper defers T3 mechanistic activation-patching.

The released assets are not mobile candidates: approximately 52 A100-hours, 67M parameters per directed bridge, about 5 GB of bridge assets and a 1.3 GB global MLP. The paper declares code/selected artifacts Apache-2.0 and the derived corpus CC-BY-SA-4.0, with underlying model terms varying. The linked GitHub source could not be independently fetched via the connected GitHub API in this run (404), so no code reuse is approved. No weights or datasets were downloaded.

## Exact V14 distinction

The current `native_latent_receiver.py` path receives per-token final output embeddings from `LlamaRunner.tap`, feeds them into the receiver's input embedding boundary using `llama_batch.embd`, then compares output embeddings against zero/shuffle controls. It does not perform the paper's mid-layer residual injection and does not generate or score target task outputs. A measured `input_effect_rms` therefore proves numeric input sensitivity only. It must not be renamed semantic utility or learned B3 communication. The packet's `semantic_use_proven=false` and `production_route=false` remain correct.

## Next implementation sequence / ownership

1. **Core:** prove same-model token-prefill versus input-embedding parity on the exact pinned llama.cpp build; keep the native probe locally armed, one-shot and B3 OFF.
2. **Core + Perception:** add a separately gated target-generation path and an explicit utility receipt. Compare NO_MESSAGE, SOURCE_EXACT, same-model parity, projected input, zero, shuffled, row-shuffled and sign-reversed/bidirectional controls on identical source-disjoint prompts. Measure task correctness/evidence recovery, not just embedding RMS/cosine.
3. **Perception:** review source/model/position/layer provenance and ensure any mid-layer claim uses a real target-layer injection hook. Existing `native_layer_taps.cpp` is an extraction reference, not an injection proof.
4. **JEPA/Memory:** only after native target utility is proven, train a small pair-specific low-rank adapter and record actual gradients, parameter diffs, held-out/OOD gain, old-session retention, restart and rollback. No model-body weights or installed model are changed by this handoff.

## Evidence boundary

- LOCAL_LINUX: no full Aii checkout is mounted in this worker; no local repository tests or native model run were executed for R-091.
- CI: this research branch has no code tests; Boss integration CI remains authoritative for its own head.
- TERMUX/REDMI: no native model, Android receiver or phone test was performed. REDMI_UNVERIFIED.
- No device request, model download, permission change, weight edit or deployment occurred.

Next step: Core should implement same-model input parity and a separate target-generation utility gate before anyone claims native latent communication.
