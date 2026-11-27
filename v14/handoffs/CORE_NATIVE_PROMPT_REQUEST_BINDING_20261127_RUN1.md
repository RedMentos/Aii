# Core & Harness — exact native C3 prompt request binding

Date: 2026-11-27
Branch: `core/v14-native-prompt-binding-current-20261127-run1`
Base: Core #2543 `d651185e881ab85bcf349f21088395f3e7033b0e`

## Gap addressed

The existing source-bound B1/B2 receipt recorded that C3's typed offer template was rendered and that the native completion endpoint returned HTTP 200. It did not bind the post-admission prompt hash to the exact `/completion` request body, and the local SQLite audit therefore could not distinguish request inclusion from a template-only receipt.

## Implementation

- Adds direct Core instrumentation that hashes the exact prompt string at both native completion call sites.
- Compares the request hash with the exact post-admission `native_prompt_sha256` witness.
- Extends the no-text local audit to require both B1 and B2 source-bound packet receipts, a matching request hash, nonzero C3 output, and native `prompt_n + cache_n == prompt_tokens`.
- Keeps semantic attention/use, learned latent transfer, and Redmi installation explicitly unproven.
- Updates the recovery → stage builder → RuntimeDeploy source-pin chain bottom-up; the overlay modifies only the staged source map and does not edit historical source files.

## Verification plan

- Python 3.13 and 3.14 CI compiles the direct runtime source and runs loopback HTTP, staged Runtime, SQLite audit, and negative mismatch controls.
- LOCAL_LINUX full Aii checkout: NOT_RUN; GitHub DNS resolution is unavailable in this environment.
- TERMUX/REDMI: REDMI_UNVERIFIED; no phone receipt, APK update, model/weight change, permission change, or device action.
- Exact-head CI is now PASS on implementation code SHA `cb6883f96050681b19c6a543c9b89c3d7523808a`; PR remains DRAFT / NOT_RELEASED pending independent Boss/QA review and integration.

## Exact-head CI

All checks passed on implementation code SHA `cb6883f96050681b19c6a543c9b89c3d7523808a`:
- Prompt binding Python 3.13/3.14: run 45918725547
- RuntimeDeploy integrity: 45918725591
- Phone offer receipt: 45918725546
- Core audio/observer composition: 45918725525
- Lab Age/WebView truth: 45918725692
- Two-checkout updater migration: 45918725558
- Coordinated source contracts: 45918725535
- Private owner-read bootstrap CI: 45918725542 (not a live phone receipt)
- Core native stream integrity: 45918725628
- Staged context + integrated regression: 45918725570

LOCAL_LINUX full checkout remains NOT_RUN; TERMUX/REDMI remains REDMI_UNVERIFIED and private relay returned NO_LIVE_RECEIPT.

## Next

1. Independent Boss/QA review of exact request hashing, token-count parity, fail-closed audit semantics and the refreshed source-pin chain.
2. Implement per-organ native prompt-token-span receipts with pinned llama.cpp `POST /tokenize` `with_pieces=true`; test UTF-8, BOS/special-token, partial-boundary and mismatch negative controls.
3. Reconcile the Android action journal stack with the separate capability/MediaProjection stack before release integration.
4. Obtain a separate authorized Redmi receipt before claiming native device behavior.
