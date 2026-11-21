# QA handoff — same-turn B1/B2 delivery

**Date:** 2026-11-22  
**Base:** Core #2242 `1850b9ba025074be89476ee32c87ae57b0345f29`  
**Branch:** `qa/v14-same-turn-body-delivery-20261122`  
**Status:** REPRODUCED BY SOURCE / REGRESSION ADDED / CI PENDING / NOT_RELEASED

## Defect

On a 30-second background-observer turn, two recent C3 DEADLINE rows with zero generated tokens in load/template/prefill activate `native_turn_budget.plan()`. The current policy sets a 26.1-second C3 reserve and a pre-answer end at approximately start+3.9 seconds. `Cognition.offer()` then unconditionally raises `Limits` for each pre-answer B1_DETAIL and B2_GIST call. Both offers become POSTCOMMIT_ELIGIBLE, so neither can contribute to the same turn's C4 focal loop.

This preserves a C3 time reserve but violates the whole-system same-turn requirement when the executive wakes both bodies for a nontrivial task. Post-commit observer work cannot retroactively satisfy B1+B2→C4→C3 for that answer.

## QA regression

`v13/code/tests/test_same_turn_body_delivery_qa.py` drives the actual `Cognition.offer()` entrypoint for both roles with content-free, genuine-shaped C3 failure metadata. It stops exactly at the source/generation boundary and asserts that both body roles are attempted pre-answer, with no deferral log. The test is intentionally expected to fail on the current Core candidate until Core supplies a bounded same-turn body window. It does not synthesize native tokens, claim an OfferPacket, or claim C4 consumption.

## Ownership and next fix

Core owns the measured native time-budget algorithm and must keep the C3 reserve without silently deferring both bodies. QA owns this regression and will add a downstream C4 receipt assertion once both offers can reach generation. Do not solve by permanently removing B1/B2, disabling the C3 reserve, raising the global deadline without measurement, or relabeling post-commit offers as same-turn.

## Evidence boundary

Source-level control flow is verified on Core #2242. No local full-repository test ran in this environment. The new regression's CI result is pending. No native model generation, Android/Termux execution, Redmi receipt, PSS/TTFT measurement, or model/weight/permission change occurred. `REDMI_UNVERIFIED`.
