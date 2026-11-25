# Research & Perception Run 18 — native input-embedding receipt

Date: 2026-11-25
Branch: `research-perception/v14-native-input-tap-receipt-20261125-run18`
Parent branch: `research-perception/v14-token-span-manifest-integrity-20261125-run16` (PR #2502 stack)
Code commits:
- module: `0eb1ff9f1f74b9c6dcae9c4c6e736889d80be248`
- tests: `e48771ccce390b4c27ba0770f6c3eba8addfd5db`
- research ledger: `e1b1689bda9c900ccbbcfba825c70d7bef4c8ed5`

## Concrete gap

The schema-v1 receiver input-embedding manifest bound the source, token pieces/IDs, event/generation, model/tokenizer revision and row hashes, but did not bind the native extractor that purportedly produced those rows. It could not distinguish a genuine selected-row result from rows passed alongside an unrelated caller-supplied token list.

## Change

`v13/code/v13/native_input_embedding_tap.py` is now schema v2. It requires a strict native receipt binding:
- API symbol/header and explicit staging/WIP status;
- exact llama.cpp revision and extractor-binary SHA-256;
- installed model revision and model SHA-256;
- source tensor type, F32 output, vocabulary size and embedding dimension;
- exact ordered requested token IDs and returned element count.

The receipt is included in the manifest digest. Negative controls reject ID/order drift, wrong model/hash, malformed extractor revision/binary hash, invalid vocab bounds, partial output count, dimension mismatch, non-F32 output and malformed tensor type. The API returns an element count rather than row IDs; the field is deliberately named `requested_token_ids`. A native wrapper must prevalidate every token before the call and emit the receipt only when the API returns exactly `n_tokens * n_embd`.

R-149 corrects R-148's upstream attribution: `a8fad21` is an unrelated MTP hidden-state commit; the selected-row API appears in llama.cpp `2851b3bcbf8d993a2243ae751c0a7dfa8e944a40` (2026-10-16, MIT, staging/WIP `llama-ext.h`). The current receiver pin `b29c606` predates this API.

## Tests and boundaries

- LOCAL_LINUX isolated reproduction, CPython 3.13.5: `py_compile` PASS; 19 focused positive/negative tests PASS.
- The local run used an isolated package and minimal dependency stubs; it is not the full Aii repository suite.
- Full Aii checkout is not mounted in this environment. Exact-head GitHub CI PASS on code/workflow head `787758a885294d63c614c4171c4a528ecc303dc8` (run 45658242985): Python 3.13 and 3.14 each compiled the adapter/source-audit contracts, ran 66 tests PASS, and passed the public privacy scan (CLEAN).
- No llama.cpp native build, GGUF row read, Android cross-compile, Termux or Redmi test is claimed.
- No model/weight, permission, updater or device data changed. B3 remains OFF; REDMI_UNVERIFIED; NOT_RELEASED.

## Consumer handoff

Core owns the native selected-row wrapper and runtime consumer. It must independently verify the installed model and extractor binary hashes, echo the exact request IDs, record the pinned llama.cpp revision/tensor type, prevalidate all token IDs before calling the staging API, and require the exact returned element count. The sender final-RMSNorm tap must remain distinct from receiver input-embedding rows. The event-pooled `LATENT_PREFIX_V1` path remains separate. This contract is not proof of learned utility, gradient/retention or production B3.

## Next action

CI is green. Core should now consume the schema-v2 receipt in its native selected-row wrapper and runtime producer, independently verify the model/extractor hashes, prevalidate all token IDs, and require the exact element count. Then run real GGUF sender/receiver task controls and learning/retention gates before any Redmi validation. Do not change the installed llama.cpp pin or any model on the Redmi without separate reviewed evidence and consent.
