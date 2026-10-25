# Run166 prereg — isolated real F32 master lifecycle wiring micro (no JEPA claim)

Date 2026-10-25. Exact base Run165 `16bf9c2ec42f26eb13b0ff3b0d107695a94e347c`. Owner Run166 new micro script/tests/workflow/proof only. No edits to Run160–165, frozen Runtime, model registration, original cohorts or Canon.

## Purpose and hard claim limit
Demonstrate an **isolated FP32 train-master plumbing micro** on up to four real source-verified B1 F32 norm vectors: actual differentiable gradient on a deterministic synthetic quadratic objective, bounded update, slow EMA arithmetic, exclusive private checkpoint, reload and exact baseline rollback. This is **not** a JEPA objective, semantic learning, active B1 inference change, native training runner, requantization, retention or second-attempt utility. Never set `jepa_weight>0` or learning authority.

## Frozen input / objective / gates
Use exact pinned B1 GGUF revision `6767265158422fb8a19c62ceb45f16f05363615b`, size 695755488, SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`. Run162 selects sorted first up to four 1D F32 vectors <=16MiB, Run163 verifies exact source bytes before any micro. For each selected vector, deterministic **synthetic** target `w0+0.01`; `L=sum((w-target)^2)`, one CPU Torch FP32 autograd step with lr=0.1, max combined update L2=0.2, EMA beta=0.9. Check finite nonzero gradient, finite bounded step, post-loss lower, EMA between original and updated, original model and master byte hashes unchanged, exclusive private candidate NPZ reload, and baseline rollback equality. All candidate weights private and deleted by CI trap. No other objective or posthoc tuning.

## CI and evidence
Serialized with `v13-native-c3-run131-serialized` group, no overlap with heavy owner. Recheck exact model source, isolated pinned dependencies and RAM/disk, upload **metadata only**, preserve failure logs and official privacy scan. Distinguish Linux-native Torch gradient arithmetic on actual B1 FP32 inference slices from actual JEPA/Redmi. Negative gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, DS2 H2 FAIL, V13 INCOMPLETE.

## Next after proof
Real train-master ownership/persistence/restart/requantization and gradient attribution to an actual predictive latent JEPA objective with model receiver, paired ablation and answer utility, plus retention/rollback and Redmi. No automatic activation or merge without independent review.
