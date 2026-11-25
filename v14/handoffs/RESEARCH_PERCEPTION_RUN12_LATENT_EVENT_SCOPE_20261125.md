# Research & Perception — Run 12 handoff
**Date:** 2026-11-25  
**PR:** [#2496](https://github.com/RedMentos/Aii/pull/2496)  
**Branch:** `research-perception/latent-event-scope-20261125-run12`  
**Base:** #2489 head `314e4e651da54f8168508c0d0f2e8bac2ca8ed2e`  
**Code-bearing head at checkpoint:** `a1d8fe6c82ffd4573d81ab69769d12dce50827a6`  
**Docs/board checkpoint before final handoff refresh:** `e9133d72a3a9f989dc3260f7e74819ca8cfb3700`

## Why this change exists

The persisted B1/B2 tap fitter in #2489 pools all non-position-zero final-RMSNorm rows into one vector per source/event. The old generic `project_rows()` nevertheless allowed that event-level adapter to be applied across arbitrary token rows. That mismatched the training unit and receiver input unit.

Core's native receiver v3 currently accepts a sequence of token-aligned embedding rows with contiguous positions under `ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL`. It does not define a `LATENT_PREFIX` mode. A pooled event vector therefore cannot safely be represented as a one-row tokenizer prefill.

## Implemented

- `v13/code/v13/latent_adapter.py`
  - Draft schema bumped to `v14.cross-organ-latent-adapter/2`.
  - Every adapter now records `projection_scope`: `PAIRED_VECTOR`, `EVENT_POOLED_NONZERO_MEAN`, or `TOKENWISE`.
  - `fit_from_tap_records()` explicitly produces `EVENT_POOLED_NONZERO_MEAN`.
  - `project_event()` projects one event-level vector.
  - `project_rows()` now rejects event-level adapters and accepts only `TOKENWISE` adapters.
  - Tokenwise fitting additionally requires per-source `token_position` metadata with at least two contiguous rows starting at zero; duplicate, missing and gapped positions are refused.
  - `build_native_receiver_input()` constructs the receiver-v3 token-row payload only for a tokenwise adapter bound to the explicit receiver `*.input-embedding.v1` tap. It validates row/token count and tokenizer revision, delegates vector shape/hash and contiguous-position checks to the existing Python native receiver, returns no token IDs, and retains zero production/learning authority.
- `v13/code/tests/test_latent_adapter.py`
  - Adds scope isolation, tokenwise projection, native receiver contract and negative controls, including missing/duplicate/gapped token-position cases.
- `v13/code/tests/test_latent_tap_adapter.py`
  - Uses `project_event()` for the event-pooled persisted tap adapter and asserts multi-row projection is refused.
- `v14/V14_RESEARCH_LEDGER.md`
  - Adds R-141, a scoped negative cross-model transfer result (abstract-only; see below).

## Tests and exact evidence

- **LOCAL_LINUX isolated helper reproduction:** CPython 3.13.5, `py_compile` PASS; 10/10 isolated contract/position tests PASS. The harness uses a local copy of the receiver validator contract and is not the repository module. This is a local reproduction of the new scope/receiver-builder logic with a local receiver-validator stub, not the exact repository test files.
- **Full local Aii checkout/tests:** NOT_RUN; no checkout is mounted in the execution environment. GitHub DNS/network access is unavailable from the local shell.
- **Exact repository CI for #2496:** staged/integrated workflow was still IN_PROGRESS at the last poll; no PASS is claimed for this PR. The dedicated #2489 workflow is not present on the repository default branch, so it was not independently dispatched for this child branch. Latest code head #a1d8fe6 has runtime-deployment integrity SUCCESS; staged/integrated regression remains IN_PROGRESS at last poll.
- **Core receiver PR #2488 context:** its exact reported head `b8b43910a67a1b706be22e42f4e9cbcfa6de1fa6` has 17/17 check-runs SUCCESS, pinned llama.cpp Linux build/selftest PASS and Android arm64 cross-compile PASS. That is Core's receiver build evidence, not a native model-pair test for this adapter.
- No GGUF was loaded by this run; no native sender/receiver pair, gradient, semantic task utility, retention, restart/rollback or Redmi measurement was performed.

## Research note R-141

Zhang, *A Negative Result on Cross-Model Activation Transfer in a Pythia Multi-Hop Setting*, arXiv:2606.03280 (2026-06-02), was verified from its abstract only because arXiv PDF/HTML endpoints were inaccessible. The abstract reports normalized cosine near 0.97 for Pythia-160M→410M but no downstream multi-hop gain; low-strength additive injection stayed near baseline and replacement was destructive. This is not a full-paper review or universal impossibility claim. No code, weights or data were reused; no license was verified.

## Current status and boundaries

- Adapter fit from persisted B1/B2 taps is an **event-pooled alignment candidate**, not a tokenwise native receiver adapter.
- The generic tokenwise test uses synthetic paired vectors. A real tokenwise adapter still needs source-bound sender activations paired with the receiver's actual input-embedding space and exact model/tokenizer revisions.
- If Core wants to consume the current pooled adapter, it must add a separately typed `LATENT_PREFIX_V1` receiver position mode; do not reinterpret tokenizer-prefill positions.
- If Core instead supplies receiver input-embedding taps, the tokenwise path can be evaluated with the current receiver-v3 input contract.
- Production B3 remains OFF. The native receiver remains diagnostic-only. **REDMI_UNVERIFIED / NOT_RELEASED.**
- Last available private V13OBS #115 snapshot remains 2026-11-24 09:28 UTC: installed target `8d93236c753f0194224c19edc7411d8d7082b1d6`, auto-update enabled in that snapshot, runtime STOPPED_BY_USER, zero valid B1/B2 offers. No fresh authenticated device receipt was obtained in this run; do not treat those values as current live status.

## Next executable step

Core/Harness should choose one explicit bridge contract:
1. add a source-bound receiver input-embedding tap and paired tokenwise cohort; or
2. add a separate `LATENT_PREFIX_V1` input mode for one pooled event vector.

Then run the approved one-shot native probe against an installed receiver model, followed by receiver-side task utility against exact-message/no-message/zero/shuffle/row-shuffle/repeat/parity/OOD controls. Keep B3 OFF until that evidence exists. No user action is required for this code-only diagnostic checkpoint.
