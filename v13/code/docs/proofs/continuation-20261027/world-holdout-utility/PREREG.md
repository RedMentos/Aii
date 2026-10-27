# World-JEPA independent held-out utility audit — preregistration (2026-10-27)

Base: PR #659, commit `949afa149460478661d54cfa944e321d195a7b03`, World review chain, NOT production/main or AG5-integrated.

## Problem and frozen controls

Existing real Linux file-world Z12c lifecycle trains on 80% of one cohort and calibrates confidence on later clean transitions. It does not measure prediction utility on an independently collected post-checkpoint cohort. In-sample calibration is not a utility proof. Original registered Z12c seed211 C1/C2/C3 FAIL and STEP2/B3/Body-JEPA negative gates remain unchanged.

Implement a **separate, opt-in, offline** holdout evaluator. It must load an existing v2 checkpoint from a verified real-file-world training export without changing its bytes, weights, calibration, authority, registered cohorts, seeds, or source hashes. Require a different holdout seed. Collect 120..20000 NEW transitions using the existing independent Linux file-world process in a fresh temporary directory, retain the original process schedule/log and row timestamps, recompute overlap labels, and persist the exact heldout features and hashes. The run may only act on its private temporary file sandbox, never on V13's live tools/state.

Before looking at results, fix the evaluation metrics: target-encoder normalized MSE of the checkpoint's action-conditioned prediction; identity/no-change target-latent MSE; one-row-rotated action negative-control MSE; fractions of rows where the action-conditioned model beats each control; number of real process events and overlapping rows; mean confidence and uncertainty-label count. All comparisons use the **same** heldout transitions. Record zero authority and explicit evidence scope; do not define a new PASS threshold or promote a Canon gate from these exploratory metrics.

## Predeclared checks

1. A RED test before implementation demonstrates missing evaluator, then GREEN on the exact same tests.
2. Actual Linux file-world training export -> fresh different-seed holdout -> read-only checkpoint inference -> persisted raw source/log/schedule/intervals/report -> independent restart re-verification; source and checkpoint unchanged.
3. Same seed, unverified training export, malformed or altered receipts, and invalid checkpoint/provenance fail closed; no holdout collection before failed preflight.
4. Deterministic control metrics and finite bounded outputs; no hidden fitting or calibration on holdout; unchanged `jepa_weight=0`, STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE.
5. Run focused tests, compile, repository privacy scan in pinned Ubuntu CI; preserve failed attempts and original Actions artifacts. If possible run broader tests without consuming heavy native/model resources.

Evidence levels: synthetic-content real Linux file actions, not Redmi, semantic causality, native model training or continuous-learning proof. No AG5/Claude integration claim. Independently review before merge.
