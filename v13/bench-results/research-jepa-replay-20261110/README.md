# V13 bounded-replay A→B→A research run (2026-11-10)

**Verdict: synthetic exploratory result, no promotion and no Redmi measurement.**
The preregistration was saved in GitHub commit `94813d7a361fb64f8b71e179bf80c15a11d5cec3` before this run. Source parent is
PR #1683 commit `abfd31a2651b418e1ef3f9a10bf089983d299984`. JEPA-related
follow-up PR #1685 is independent and is not claimed as present here.

## Actual run

- Linux x86_64, Python 3.12.14, NumPy 2.3.5, `OPENBLAS_NUM_THREADS=1`.
- Real `WorldJEPA` NumPy weights trained; 3 seeds (13,21,34), one predictor,
  20 pretrain and 20 steps per next phase. Each updated arm processes 32 rows
  per `partial_fit` and uses the same number of steps. Replay uses 16 current
  plus 16 past rows; the current arm uses 32 current rows. A separate frozen
  control performs no further updates.
- Per regime heldout: 64 independently generated rows. Heldout and training
  IDs and observation/action contents were checked for overlap. Three generated
  data hashes are in `results.json`. Old A, B and returned A training sets are
  distinct. Frozen linear readout fitted only on initial A training targets;
  each phase's A and B observable MSE uses this same readout and heldouts.
- `results.json` SHA-256:
  `da450d59bee4bb07751a7778e2d0bbdb26995601813a13428add4c70db965f1b`.
  Script SHA-256:
  `48e1f972a61970573bb01940f4211ef9aeaf48e1839c5c1ecc64ed6af20dce7f`.
  Re-running on the same host with the commands below produced byte-identical
  JSON. The reported replay bytes are nominal array payload, not RSS or peak
  working memory; all synthetic train arrays remain resident in this harness.

Mean heldout observed-state MSE over the three seeds (lower is better):

| Condition | After initial A: A / B | After B: A / B | After return A: A / B |
|---|---:|---:|---:|
| Frozen | .3764 / .6035 | .3764 / .6035 | .3764 / .6035 |
| Current only | .3764 / .6035 | .4572 / .4119 | .4213 / .6402 |
| Bounded replay | .3764 / .6035 | .3046 / .4388 | .4691 / .7967 |

Individual seeds are in `results.json`. Do not read the mean as a dependable
improvement: seed 34 dominates the return-A replay result, and seed 21 worsened
substantially in the current-only B phase. The action-flip control sometimes
performs better on A after training B (mean .4105 vs .4572 for current-only),
so action dependence can also reverse. That is an important failure mode.

**Interpretation:** in this deliberately conflicting environment the same
state/action has opposite desired outcomes in A and B and the active regime is
not observable. Perfect A and B prediction simultaneously is impossible for a
single deterministic predictor without memory/context. Current vs replay also
trade fresh samples for prior samples. Replay takes the first 8 or 16
rows of each phase; these subsets are not always action-balanced even though
full phases are, so action proportions can confound the comparison. The same
heldout rows are evaluated at each phase; they never enter training, but tuning
based on these results would require fresh seeds and a new final holdout. Thus
these numbers do not establish an intrinsic replay benefit or failure in V13. The fixed readout penalizes internal
representation drift, including potentially benign drift; EMA-target latent
losses are also not directly comparable across moving encoders. A follow-up
should add an observable context, a replay-size sweep, explicit independent
old/new transition sources and longer multi-seed sequences, and measure device
resources before considering runtime changes.

## Reproduce

From the repository root:

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=v13/code python -m unittest discover -s v13/code/tests -p 'test_jepa_bounded_replay_ablation_20261110.py' -v
OPENBLAS_NUM_THREADS=1 PYTHONPATH=v13/code python v13/code/scripts/jepa_bounded_replay_ablation_20261110.py --output /tmp/v13-replay.json
sha256sum /tmp/v13-replay.json
```

`test-output.txt` records 4 passing tests. Tests cover actual updates, matched
fit-step counts, frozen behavior, replay budget, deterministic seeds and
heldout-overlap negative controls. The current shell had no `pytest`; the new
checks use stdlib `unittest`. No full repository suite or GitHub Actions result
is claimed.

## Research basis

- Zhang et al., JEPA-TTT, preprint v1 2026-09-30; accepted to a NeurIPS 2026
  workshop: https://arxiv.org/abs/2610.00722 and
  https://jepa-ttt.github.io/ . Authors compare a dense stream and dense replay
  in simulated control. One fixed shift per run; no A→B→A retention, no Android
  evidence. Paper license CC BY 4.0. No author-linked code or weight repository
  verified on the project page on 2026-11-10; license of such code unknown.
  Our experiment uses an updating encoder and resets optimizer state between
  `partial_fit` calls, unlike their frozen encoder / persistent optimizer; it
  is not a replication. No third-party code or weights copied.
- Si and Qin, *Continual-learning rules shape representational drift*, preprint
  v1 2026-08-17, revised v2 2026-09-01:
  https://arxiv.org/abs/2608.16141 . Their CNN/RNN experiments show old task
  performance can persist alongside representational drift, whereas strong
  anchoring can reduce new learning in their tested settings. Task-ID and fixed
  task-order evaluation limit transfer. Their original repository
  https://github.com/yksi2023/cl-drift/tree/236cda6aff92030d43dd61c585259742a8aff181
  had no license verified; no code is reused. Its documented CUDA/ImageNet
  requirements are not evidence of Redmi compatibility.

**Next V13 seam:** use this as an independent control for the JEPA & Memory
owner, not as a gate. Add regime/context features and old-task heldouts to a
subsequent experiment linked to the actual committed T8 feed only after IDs,
episode-level source disjointness, privacy and checkpoint/restart consistency
are established. `online_world`'s current replay-buffer loss is train-adjacent,
not an independent old-task holdout.
