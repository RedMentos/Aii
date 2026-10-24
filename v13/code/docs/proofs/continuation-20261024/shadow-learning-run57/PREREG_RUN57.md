# Run57 — end-to-end source-bound SHADOW learner with durable receipt (synthetic)

2026-10-24. Base PR90 `dc474011057eee7c5d5cf37e9bfa24e030891a52`; owner only `v13/code/docs/proofs/continuation-20261024/shadow-learning-run57/*`. No production files touched, no model/teacher downloads, no real user data.

Goal: combine Run56 durable source-revocation receipt with an actual tiny CPU gradient optimizer trained exclusively on exact source-validated synthetic records. The trainer must derive its inputs/labels from SourceRefs and bind dataset hash and SourceRef set into safe checkpoint metadata; never accept arbitrary unbound labels or promote Age rights. The receipt must be rejected if any training source is revoked before commit or consumption. Base model file remains bit-identical.

Preregistered synthetic cohort: 16 keys, 4 training examples/key (64 train), 4 independent heldout examples/key (64 test); deterministic permutation of labels, random nonce text; fixed seeds 20261024 (dataset) and 1337 (weights); 120 Adam steps, lr .10, full-batch cross entropy, PyTorch CPU; wrong-target control with independent shuffled labels same schedule. Primary success thresholds: trained heldout accuracy >=.90; untrained <=.25; shuffled-target <=.50; zero unverified sources, zero production weight writes; full source revocation before/after commit refuses. Do not change cohort or thresholds after running; failures retained.

Evidence classes: Linux synthetic PyTorch + SQLite + safetensors, not native C3/B1/B2, real Store/Runtime, Redmi, causal JEPA, general AGI or canonical utility. No STEP2/B3/Body-JEPA/jepa_weight gate promotion. Need full checkout independent review and actual SourceRef/Store/learning-path wiring later.
