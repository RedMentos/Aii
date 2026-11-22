# Research & Perception handoff — A4 novelty-gate ablation

Date: 2026-11-22
Base: `gpt6/v13-private-remote-bridge-20261111` at `aed1d2b826290c95c70356b5d8b864b5ef382be4`
Branch: `research-perception/v14-a4-novelty-ablation-20261122`; latest docs head `bb85ddd893d59836bac905dfb7c78342d6c0e996`

## Research reviewed

Full 12-page preprint reviewed: Louis Mouchon & Alexis Lainault, *Surprise-Gated Memory for Live Speaker Diarization*, arXiv:2611.20819v1. The arXiv record says submitted 2026-11-16; the PDF title page says 2026-09-26. It is an independent preprint, not peer-reviewed evidence.

The method uses a frozen DiariZen/WavLM + Conformer speaker stack, embeddings projected into the backbone's LDA/PLDA scoring space, development-set z-scored novelty, a three-regime assign/defer/create gate, and periodic full-buffer VBx consolidation. Reported gate AUROC is 0.866 on its AMI development data; thresholds are 0.15 / 0.45 in z-score units. Segments under 0.5 s net speech or overlapped are forced to DEFER. Headline results use a 60-second sleep interval.

The reported revisable DER is 18.1 vs 20.8 without sleep and 23.5 with a two-minute sliding replay window on AMI-SDM; 8.0 vs 11.1 and 18.4 on VoxConverse. However, the causal-strict track is poor: 58.2 / 47.8 vs naive online 22.9 / 9.9, largely due to cluster renumbering during consolidation. Removing deferral is nominally slightly better on the revisable track (17.1 / 7.7), but substantially worse causally (62.8 / 46.1). The authors explicitly say the small single-seed test sets (3 AMI meetings, 5 VoxConverse sessions) support condition ordering more than absolute rates. Their residual analysis places most remaining error in overlap/VAD segmentation, not memory.

## V14 compatibility decision

Do not transplant the paper's thresholds or claim its result for V14. It uses model-specific PLDA and VBx; V14's current RAW EAR evidence is cosine-lookback over caller-supplied embeddings, with no verified calibration artifact and A4 correctly remains DEFER. FASTDIAR code is MIT at the reviewed tag, but the checkpoint-weight license is unresolved; no weights were downloaded or used.

## Implemented experiment

Added `v14/experiments/a4_novelty_gate_ablation.py` and its tests. It compares:
- no novelty gate vs a single threshold vs assign/defer/create;
- all-history prototypes vs a global 24-event sliding retention proxy vs first-exemplar retention;
- thresholds tuned only on source-disjoint synthetic training sessions and evaluated on held-out synthetic sessions.

This is a cosine-prototype mechanism stress test, **not** PLDA, VBx, FASTDIAR inference, real audio, speaker recognition, an A4 Runtime consumer, or a reproduction of arXiv:2611.20819v1. The labels are synthetic and all vectors stay in memory.

## LOCAL_LINUX evidence

Environment: CPython 3.13.5 x86_64.
- `python -m py_compile a4_novelty_gate_ablation.py test_a4_novelty_gate_ablation.py`: PASS.
- `python -m pytest -q`: 4/4 PASS.
- Three source-disjoint runs (12 sessions each; seeds 20261122, 20261123, 20261124) produced a stable trade-off:
  - Full-history + triage: change F1 0.5455 ± 0.0000, false-novelty 0.0000, overlap deferral 1.0000, overall deferral 0.5574 ± 0.0092, coverage 0.4858 ± 0.0101, cluster count 4.0.
  - Full-history + single threshold: change F1 0.5354 ± 0.0143, false-novelty 0.0004 ± 0.0005, coverage 1.0, cluster count 4.0.
  - Sliding-window + single threshold: change F1 0.9616 ± 0.0211, but one-shot recall 0.4397 ± 0.0163 and cluster count 8.94 ± 0.08 for four synthetic speakers (fragmentation).
  - Sliding-window + triage: change F1 0.7421 ± 0.0107, overlap deferral 1.0, but coverage 0.3946 ± 0.0094 and cluster count 5.78 ± 0.08.
- The toy result is a trade-off, not evidence that sliding replay is beneficial. It is not comparable to the paper's VBx full-buffer sleep.
- No full Aii checkout, normal Runtime, Termux, Android, Redmi, real microphone or camera test was available.

## Integration boundary and next action

This PR is research code only. It does not alter production A4 thresholds, speaker identity, persistent memory, learning rights, model weights, permissions, or runtime behavior. Next: rebase/reconcile the separate FASTDIAR adapter PR #2361 against the latest release-development base, and only after a real, consented labelled embedding source exists, build a model-bound calibration/receipt path. Keep A4 decisions DEFER until then.
