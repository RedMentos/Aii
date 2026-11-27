# Core & Harness — exact native C3 prompt request binding

Date: 2026-11-27
Branch: `core/v14-native-prompt-binding-current-20261127-run1`
Base: Core #2543 `d651185e881ab85bcf349f21088395f3e7033b0e`

## Gap addressed

The existing source-bound B1/B2 receipt recorded that C3's typed offer template was rendered and that the native completion endpoint returned HTTP 200. It did not bind the post-admission prompt hash to the exact `/completion` request body, and the local SQLite audit therefore could not distinguish request inclusion from a template-only receipt.

## Implementation

- Adds a pinned staged overlay that hashes the exact prompt string at both native completion call sites.
- Compares the request hash with the exact post-admission `native_prompt_sha256` witness.
- Extends the no-text local audit to require both B1 and B2 source-bound packet receipts, a matching request hash, nonzero C3 output, and native `prompt_n + cache_n == prompt_tokens`.
- Keeps semantic attention/use, learned latent transfer, and Redmi installation explicitly unproven.
- Updates the recovery → stage builder → RuntimeDeploy source-pin chain bottom-up; the overlay modifies only the staged source map and does not edit historical source files.

## Verification plan

- Python 3.13 and 3.14 CI compiles the overlay and runs loopback HTTP, staged Runtime, SQLite audit, and negative mismatch controls.
- LOCAL_LINUX full Aii checkout: NOT_RUN; GitHub DNS resolution is unavailable in this environment.
- TERMUX/REDMI: REDMI_UNVERIFIED; no phone receipt, APK update, model/weight change, permission change, or device action.
- PR is draft / NOT_RELEASED until exact-head CI and independent Boss/QA review pass.

## Next

1. Resolve exact-head CI failures, if any.
2. Boss/QA review the overlay, source-pin chain, and audit's deliberately narrow proof semantics.
3. Integrate this leaf with #2543 and then rebase the Core consumer chain onto the current Perception parent only after that branch is green.
4. Obtain a separate authorized Redmi receipt before claiming any native device behavior.
