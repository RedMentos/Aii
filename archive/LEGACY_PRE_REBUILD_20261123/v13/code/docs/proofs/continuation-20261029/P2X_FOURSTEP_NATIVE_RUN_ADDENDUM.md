# P2X 16×4 native execution addendum (2026-10-29, before job)

Independent child PR #1089 of #1088, parent native prereg `P2X_C3_FOURSTEP_PREREG.md` is binding. The source-only parent CI [40868563641](https://github.com/RedMentos/Aii/actions/runs/40868563641) passed exact head `c4243164f8d100dc826f3e1ee2d7d169228cd649`: 33 focused, 3139 full software (11 skipped), nine zero stage exits, 21/21 hashes, privacy CLEAN. Original artifact ZIP SHA256 `a959d2380147647c79d3332a36cfa4a7b6844205322ce3c977907f90cf1a5120`, CRC CLEAN, privately backed up and byte-verified. No native 16×4 job has been claimed as completed.

## Native job intent and unchanged prereg

Execute exactly the parent preregistered 16 training examples, 4 full-batch optimizer steps, seed2026102924, rank2/alpha4/lr0.0003, QAD FP32 master revision `657e078c94084481950a2d555a941481f715536b`, original pinned file SHA256, train export SHA256, no heldout use, jepa0, no anchors, no AG6/live activation. Reuse prior proven isolated PyTorch/transformers/peft/gguf dependency versions and Linux CPU. Do not modify the parent training script or registered source/model/seed. Source hash preflight, >=5GB free RAM/disk, serialize via existing `v13-p2-qad-fp32-real-value-serial-20261029` concurrency group; never cancel an active owner.

After native fit, run child read-only offline verifier against original result and both adapter files **before copying**. Capture stage exits, all raw logs, SHA256SUMS, source/master/cohort hashes, adapter GGUF+PEFT and original license, and a modified-adapter notice. Preserve any RED. An artifact-consistency audit does not independently attest optimizer execution; original native raw, runner logs, frozen source and step metrics still need separate review. The native run is research only; do not use P2X heldout validation answers or P0X holdout during fitting. No STEP2/B3/Body-JEPA/LP3/AG6/Redmi/V13 promotion, no production merge.

If source-only child CI is RED, retain it, fix on a separate audited follow-up before treating the offline verifier as trustworthy. Native result cannot be declared GREEN on a failing independent verifier.
