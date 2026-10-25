# Run262 — measured Linux actual-Store source revalidation cost (2026-10-25)

- Exact tested head: `2a47492c73af7defa903b4484188dfd3c6338647` (PR262, based on PR259 `28a9ebcbe51661adb716ae5bdd9ca999dbf2af3c`).
- GitHub Actions run: https://github.com/RedMentos/Aii/actions/runs/40185660291; exit **0**, privacy **CLEAN**.
- Closed raw artifact: `12595523307`; ZIP SHA256 `857d32291b6cefd393a8e3b63a08c4747bbc9e633b893efc411da303a179b04c`.
- Script SHA256 `9ba2f0320e497fdc712fc8fd1ccee6b55a5ed9fcc8d46d9c3c38c4ff8c480d51`; exact WorldModel source SHA256 `fe2c41c1e0dafa6658dff6106fdb9827dbddcc1bc397211c9228020e1bda564d`.
- Evidence scope: GitHub Linux actual production Store + synthetic FINAL actions, **no native model inference, no Redmi, no real learned utility**. Times are exploratory medians of five calls on this host, not phone performance.

| Source-bound training rows | Fit (ms) | load median (ms) | counterfactual median (ms) | revoked load median (ms) |
| ---: | ---: | ---: | ---: | ---: |
| 16 | 14.9427 | 2.4412 | 2.6797 | 2.3166 |
| 128 | 53.7480 | 18.1326 | 17.8032 | 17.8514 |
| 512 | 208.7967 | 70.6717 | 74.7330 | 74.2185 |
| 1024 | 415.1625 | 140.6685 | 143.5609 | 140.0826 |

- All four cohorts fitted source-bound v2 state; deleting a trained source made `load` return None and explicit-st counterfactual return `TRAINING_SOURCE_UNVERIFIED`. All pre-revocation counterfactuals were `SIMULATION_UNCERTAIN`; this is **not** a utility success.
- Interpretation: per-call source revalidation cost scales roughly linearly and reached ~141 ms for 1024 rows on GitHub Linux. A 2048-row maximum may be material for mobile, but no Android extrapolation is claimed.
- Optimization requires a separately reviewed, crash-safe invalidation mechanism covering source deletion, event/packet/action mutation, backup/restore, and external DB tamper; no silent caching of stale model state.
- Next: integrate Run261 terminal failure counterexample under PR259 owner, then rerun exact full suite and evaluate safe revocation-aware performance on target hardware. STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, full V13 `INCOMPLETE`.
