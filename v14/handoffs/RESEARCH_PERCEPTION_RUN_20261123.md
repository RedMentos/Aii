# Research & Perception handoff — 2026-11-23

## Current code work

- Perception PR #2386: fixes the RAW EYE provider API decorator mismatch on top of QA PR #2384. Exact source change removes the context-manager decorator from the direct-return provider entrypoint and puts it on the yielding scoped cleanup API. Dedicated tests cover direct result forwarding, success/failure buffer zeroization and scope revocation. The PR is stacked on QA #2384, which is itself the follow-up to Perception #2375.
- Exact branch: `research-perception/v14-raw-eye-provider-entrypoint-fix-20261123`. Exact head: see PR #2386; current base is QA #2384 head `5cd8ffae01be205c5a2d043a7c6e7b3fbaa424e2`.
- Local environment has Python 3.13.5, PyTorch and pytest, but no mounted Aii checkout. A copied isolated-function reproduction passed for direct provider return, verifier-failure zeroization and scoped revoke. This is SYNTHETIC/LOCAL_LINUX, not a full repository test. Exact-head CI must still run.
- No Redmi device receipt, Android MediaProjection capture, Runtime/C3 consumer, model/weight change or deployment is claimed. REDMI_UNVERIFIED; NOT_RELEASED.

## Research ledger additions

- R-096: peer-reviewed engramBNN (APL Machine Learning, 2026-11-06), context-conditioned stochastic top-k gating plus metaplastic BNN; linked code is AGPL-3.0 and its 2025 repo snapshot is not shown to match the 2026 paper.
- R-097: Orion (arXiv 2026-05-26; author page says in submission), a multi-metric resource controller for replay-based supervised vision OCL; 8-GB Jetson evidence is not Redmi evidence.
- R-098: DLER (arXiv 2026-11-03), dual-logit replay and retention-aware buffer selection; linked UER repository has no visible license and pins old dependencies.
- R-099: auditory attention/PE preprint, abstract-only; not treated as a full-paper finding.

## Next executable integration

1. QA should verify/merge #2386 into #2384, then re-run exact-head workflow and update #2375 without losing its frame-source tests.
2. Core #2379 should rebase on the corrected Perception/QA chain and route its signed `UIFrameGrant` through the public provider entrypoint while the lease is active; this still needs a normal Runtime/C3 call site.
3. Boss should fold this ledger branch into the current docs branch and reconcile R-096..R-099 without changing the V14 master or historical V13 Canon.
4. After the provider path is green, the highest-value follow-up is a real Runtime dispatch hook and a same-turn source-bound UI frame → A5/A4 → C3 consumer test; Android capture remains a separate device acceptance gate.
