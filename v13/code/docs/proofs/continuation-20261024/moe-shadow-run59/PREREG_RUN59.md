# Run59 — §91 Phase B sparse expert SHADOW delta with retention gate

2026-10-24. Base PR92 `1c346721a90e76924f800f5a3c1cbc1aa7591bdb`. Own only `v13/code/docs/proofs/continuation-20261024/moe-shadow-run59/*`. No production runtime, model weights or other owner's files edited.

Canon §91: router and shared trunk frozen; small selected active expert delta in SHADOW; route distribution, collision, entropy, old-task retention, shared drift, expert delta norm, router drift and pre-router drift monitored. Activation/eligibility alone never commits: require measured error, typed modulator, explicit SHADOW permission and retention.

Predeclared synthetic cohort: 8 experts top-1 deterministic router, 8-dimensional identity trunk, each frozen base expert identity; old task uses experts 0..6, new isolated task uses expert 7. 80 SGD steps lr=.5 on expert-7 delta only, fixed seed 20261024; target output 2x for new expert. Primary PASS: new MSE falls >=90%, old-task exact retention >=.999, router/shared/base drift exactly 0, unselected deltas exactly 0, route shift exactly 0. Collision control trains expert 3 while old task includes expert 3; must FAIL retention gate. Permission denied, missing typed modulator, no measured error must refuse shadow receipt. Wrong-expert ablation must not improve new task. Synthetic only, not actual B1/B2 MoE or native sparse training. No original gate promotion.

Tests include PyTorch CPU deterministic replay and Python -O, adverse mutation of frozen router, source of activation not equal commit authority. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE.
