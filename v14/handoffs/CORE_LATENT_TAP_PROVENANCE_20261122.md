# Core handoff — source-bound latent tap model identity

**Date:** 2026-11-22  
**Owner:** Core & Harness  
**Base:** boss/v14-recall-store-pin-rebind-20261122 at 6e6f15322c9fa1931dcf733105d2a32d5372edeb  
**Branch:** core/v14-latent-tap-provenance-20261122  
**Status:** staged-runtime implementation committed; exact-head CI pending; NOT_RELEASED; REDMI_UNVERIFIED.

## Defect addressed

The native receiver candidate consumes tap["sender_model_sha256"] and tap.get("tokenizer_revision"), but the current Cognition.tap() emitted neither field. A receiver could therefore fail at the consumer boundary or lack a source-bound identity for the sender model. A tap also needed to be rejected if the installed model changed between capture and later read.

## Runtime change

- A source-pinned overlay is now applied after the existing integrated recovery, A5 consent and C4/C3 receipt composition.
- Cognition.tap() reads the sender's exact model revision and main-file SHA-256 from the local installed-model manifest, verifies the current model file against that hash before the native tap, and checks revision/hash again after the tap.
- LatentTapPacket now carries sender_model_sha256 and tokenizer_revision. Tokenizer revision is null when the installed manifest does not provide one; no guessed tokenizer identity is substituted.
- Cognition.read_tap() rechecks installed revision, model hash, tokenizer revision and current model bytes before returning vectors. Stale or modified model identity fails closed.
- The normal runtime deployment chain is re-pinned: outer integrated builder SHA-256, stage builder SHA-256 and runtime_deploy.py stager SHA-256.

## Tests and evidence boundary

- Added an exact staged-Runtime test covering manifest-backed model identity, stored packet validation, successful readback, model-revision change, model-file tampering and refusal before native tap when the manifest hash is wrong.
- Updated the existing native tap fixture for the expanded typed packet contract.
- The dedicated workflow compiles the staged chain and runs the focused tests on Python 3.13 and 3.14. Exact-head result must be read before any PASS claim.
- The container has Python 3.13.5 but no full Aii checkout and GitHub DNS resolution fails; full local repository tests are therefore BLOCKED. Do not relabel CI as LOCAL_LINUX.
- No llama.cpp model decode, Android cross-compile, Termux run, Redmi receipt, model/weight download, model swap, permission change or user-data mutation occurred.

## Canon and claim limits

This is a prerequisite for source-bound B1/B2 tap consumption under B3/Enlightened Space. It is not a trained latent projection, semantic transfer, production B3 route, JEPA update, weight-learning result or AGI evidence. The native receiver candidate remains a separate review item and must still close its executable trust and no-symlink parent-path findings before execution.

## Next executable action

Read the exact-head Python 3.13/3.14 workflow results, repair any failure, then rebase the native receiver diagnostic candidate onto the current Boss head and retain production_route=false, training_authority=0, model-hash pinning and negative controls. Native GGUF and Redmi behavior remain unverified until actually executed on authorized hardware.
