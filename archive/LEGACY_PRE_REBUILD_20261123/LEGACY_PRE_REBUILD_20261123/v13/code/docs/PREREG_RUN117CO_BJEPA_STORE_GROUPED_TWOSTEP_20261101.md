# Run117CO prereg — Store-authenticated grouped Body-JEPA two-step synthetic research

2026-11-01 UTC. Review-only child of Run117CN PR #1567 at exact parent `b82aed3a622b1dbf3b5ef359f3733d2017b3dca2`. Owner Run117CO. Preregistered **before** implementation/tests. Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged; no frozen Body trainer, cohort, seed, native runner/model or Runtime changes.

## Gap and controlled mechanism

Run117BD grouped source candidate `823644a51acd1ea1ed2c8ed17452d0976a25778f` masks repeated same-source views as false negatives but trusts caller-provided source hashes. The contrastive loss `acd40aeac9e286e93b40bda72c655c17725a522e` is differentiable, but there is no trusted Store-bound two-step consumer. Add a **default-OFF**, isolated research-only wrapper that authenticates every train/heldout source claim against real persisted full-span SourceRefs and source bytes before and after each synthetic optimizer step. No source IDs/texts exported in metrics. Use existing grouped loss; never alter the frozen native Body trainer.

Fixed synthetic Torch seed `117047`, CPU float32, B1_DETAIL path, three train views (A1,A2 same real source A, B1 real source B), heldout C1 real source C, two distinct genuine negative groups, eligibility=1, target frozen/detached. Exactly **two** SGD updates to a temporary small student tensor, LR=0.05, no model/LoRA weights, no checkpoint/export. Source pre/post checks must reject spoofed hashes, revoked refs, mixed B1/B2, source rebind, heldout overlap and revocation between steps. Real Store close audit. Require finite loss, nonzero student gradients, zero target gradient, masked_false_negatives=2, no authority. If Torch is absent in scratch, install pinned isolated `torch==2.5.1+cpu` on GitHub Actions; absence is prerequisite, not a skipped proof. Preserve any failed attempts.

## Claims and gates

This is **synthetic tensor learning** only, not Body-JEPA native training or utility. Report `synthetic_tensor_updates=2` and `model_weight_updates=0`; Age0 learning authority remains zero, runtime `jepa_weight=0`. Source authenticity is proven only for the temporary real Store fixtures, not for future external data. No STEP2/B3/Body-JEPA/World-JEPA/Redmi/whole-system promotion. Next: implement, run focused Torch/Store tests and original raw audit; if successful, independently review before any real Body model integration. Remaining platform budget UNKNOWN.
