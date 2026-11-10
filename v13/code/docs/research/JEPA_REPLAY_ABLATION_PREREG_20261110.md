# Preregistration: bounded replay under changing synthetic dynamics

Prepared 2026-11-10 before executing this experiment. Scope: research-only, no
runtime promotion, no edits to frozen SourceHandoff code. Owner: Research &
Perception. Starting source: integrated candidate PR #1683, commit
`abfd31a2651b418e1ef3f9a10bf089983d299984` (which does not include the
separate JEPA agent's later cursor fixes).

## Question and controls

Can a **bounded** replay sample preserve old synthetic action-conditioned
prediction after A→B→A transitions without eliminating adaptation to B, using
V13's existing NumPy `WorldJEPA`? Measure; do not assume an advantage.
Compare three paired arms, starting at identical fitted weights per seed:
1. frozen: no additional updates;
2. current: train only on each incoming phase;
3. bounded replay: train on an equal-sized mixture of current and stored prior
   samples (32 transition rows per update input, at most 16 stored per prior
   phase). Prior phases sampled evenly where possible.

Predeclared default: seeds 13, 21, 34; initial A, phase B, return A each have
32 independently generated training observations; per-regime 64 independent
held-out observations. Each trained arm uses exactly 20 initial and 20 per
subsequent phase gradient steps, ensemble=1, with the same fit seed. Replay and
current see the same number of optimizer steps and rows presented per fit;
replay replaces some fresh rows, so fresh-data exposures differ. Frozen is an
untrained-update baseline, not compute-matched. Randomness belongs to explicit
per-seed, per-split generators; no test observation enters training or replay.
The frozen arm keeps initial weights; outputs are stored separately. Draw
independent data for returned A. An unshuffled vs permuted-action held-out
control checks whether action information has measurable effect.

At initial, post-B and post-return, record old-A and B independent held-out
mean-squared error in original observed-state space, using one fixed readout
trained only from initial A training targets against initial frozen target
latents. Record model's own target-latent loss as a secondary, non-comparable
across-model diagnostic because its EMA encoder moves. Include representation
collapse/rank diagnostic, total updates, replay size, nominal NumPy buffer
bytes, source hashes and experiment configuration. Report per seed and
aggregate; do not cherry-pick seeds. A frozen readout is a drift-sensitive proxy
and may penalize benign representation changes; it is not an external task
utility, a causal proof, or a production accuracy estimate.

Use deterministic simple 4D numeric state, two action one-hots, and two opposing
action offsets to create two dynamics domains. No raw user data. Report actual
results without success gate; failures and negative findings remain recorded.
Future re-evaluation needs extra unseen seeds, genuine persisted T8 data,
training/holdout grouping across episodes and native hardware measurements.

## Primary source and limits

Zhang et al., *JEPA-TTT: Persistent Test-Time Training of Latent World Models
for Planning under Dynamics Shifts*, arXiv v1 2026-09-30, NeurIPS 2026 World
Models in Physical AI workshop: https://arxiv.org/abs/2610.00722 ; authors'
method and ablations: https://jepa-ttt.github.io/ . The paper holds its visual
encoder and reward head fixed and updates only the predictor, with a persistent
optimizer, dense windows and a growing buffer. It evaluates one fixed dynamics
change per run on four simulated environments, eight shifts, 3 deployments per
shift and disjoint held-out evaluations. It does not evaluate recovery to an old
regime or Android. Project-page mean AUC for dense stream 0.548 vs dense replay
0.571 under matched cumulative update budget; results are not a phone speedup.
The paper text is CC BY 4.0 per its arXiv license link. An author-linked code or
model repository and its license were not found on the project page at access
2026-11-10; do not treat code or weights as usable without verification.

This proposed tiny experiment is independently implemented, **not a paper
reproduction**. V13 `partial_fit` resets Adam and inverse-head state per call
and updates the encoder; that differs from JEPA-TTT. Replay is deliberately
bounded rather than the paper's growing buffer. No third-party code is copied.
Do not assume sparse/quantized/mobile suitability from this experiment.
