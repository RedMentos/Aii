# Core handoff — source-bound organ flow audit

**Date:** 2026-11-22  
**Base:** Boss integration branch `boss/v14-recall-store-pin-rebind-20261122` at `6e6f15322c9fa1931dcf733105d2a32d5372edeb`  
**Branch:** `core/v14-flow-audit-boss-20261122`  
**Status:** DRAFT / flow-audit CI PASS on Python 3.13 and 3.14 / newest privacy scan pending / broader staged integration pending / NOT_RELEASED / REDMI_UNVERIFIED.

## User-visible function

The local dashboard gains an explicit **Organdurchlauf prüfen** action. It reads the newest terminal assistant turn from the local SQLite Store and projects bounded A5, C2, B1/B2, C4, C3, C5 and B3/latent evidence: actual model labels, native token-count provenance, prompt/generated token counts, TTFT/duration, query-role binding, C4-consumed offers, C3 source-bound context, ActionOutcome counts and tap/symbolic/receiver counts. It does not auto-poll the audit endpoint.

## Integrity and claim boundary

- SQLite is opened read-only with the existing Android path/ownership/symlink checks and `query_only`; source blobs are checked by hash without returning their bytes.
- The HTTP route is loopback-only, random-token scoped, GET-only, no-store, no-referrer and nosniff. No public listener, remote relay or background upload is added.
- The dashboard projection returns counts, allowlisted roles/status/model labels and timings only; no chat text, prompts, source IDs, source hashes, token IDs, raw audio or device paths.
- Source-bound C3 context is not proof of semantic attention. `native_injection_proven` remains false. Synthetic fixtures remain `SYNTHETIC_FIXTURE`; runtime metadata is not device attestation.
- No fresh owner-verified device receipt was available during this run. Therefore REDMI_UNVERIFIED.

## Tests and environment

- LOCAL_LINUX: BLOCKED — no repository checkout; direct Git transport/DNS unavailable in this session.
- CI: code-bearing head `b9ccc53592f52c5682df4ae865e344a89f39e5b7` passed the flow-audit workflow on Python 3.13 and 3.14 (projection, terminal-turn filtering, read-only route, token/host/POST denial, Python compile and inline JavaScript syntax). V13 private-bridge offline security workflow PASS. The public-repository privacy scan was added on the next workflow commit and is pending; broader staged-runtime/integrated-regression workflow is still running.
- TERMUX/REDMI: NOT RUN; no connected authorized handset receipt.
- No model, weights, Age, permissions, installed runtime or device data changed.

## Next executable action

Verify the newest privacy-scan and broader staged-runtime/integrated-regression checks, have Boss review the existing dashboard route and privacy boundary, integrate into the shared Boss candidate, and use the installed dashboard to measure actual B1/B2→C4→C3 delivery before changing native time budgets or model choices.
