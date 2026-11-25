# Native tokenwise tap pairing

This Perception-side helper assembles a tokenwise training/diagnostic pair
from two different native spaces:

- sender: final-RMSNorm prefill activation rows from a stored LatentTapPacket;
- receiver: selected input-token-embedding rows from the pinned native
  llama_model_get_tok_embd_rows extractor.

It is not the event-pooled LATENT_PREFIX_V1 path. Do not send its multiple
token rows to the one-vector latent-prefix receiver.

## Caller contract

1. Read the exact source through Store.read_source(source_ref).
2. Obtain a sender LatentTapPacket through Cognition.tap, then call
   Cognition.read_tap(packet) and pass that exact result as sender_tap_data.
   The helper checks the packet's source/event/generation/role/tap/model
   bindings, whole-sequence prefill receipt, blob path/digest shape and zero
   receiver/learning authority.
3. Request sender and receiver /tokenize results with add_special=false
   and with_pieces=true. Each piece must retain its native token ID. The
   sender tap itself is add_special=true; the helper maps the unique content
   token subsequence into its prefill rows, including the special-token offset.
4. Resolve the already-installed receiver model and independently verify its
   ModelRegistry revision and SHA-256. Run
   extract_native_input_embedding_rows() with the exact ordered receiver
   content-token IDs. Pass the complete wrapper output object, not split rows
   and receipt fields.
5. Call build_native_tokenwise_pair_record(). It requires a full SourceRef
   matching the exact UTF-8 bytes and aligns sender/receiver rows by byte-span
   overlap, not token index. This supports different tokenizers and byte
   fallback across Unicode code points.

The result is an in-memory PAIRED_DIAGNOSTIC record with a digest, source,
session, event, generation, model, tap, tokenizer, extractor receipt, row
hashes and aligned numeric pairs. It stores no raw source text or token pieces.
It does not persist the record, fit an adapter, run receiver inference, change
weights, grant training authority or enable B3. The caller must not persist or
train on private source-derived vectors without the separate explicit local
learning consent and lab gate.

## Upstream API and mobile caveat

llama_model_get_tok_embd_rows is present at llama.cpp commit
2851b3bcbf8d993a2243ae751c0a7dfa8e944a40 (MIT). Its declaration is in
src/llama-ext.h, whose header explicitly labels the API staging/WIP. The
implementation returns n_tokens × n_embd F32 elements and converts only the
requested rows through llama_tensor_rows_to_f32; it returns zero for invalid
IDs, and may have copied earlier rows before discovering a later invalid ID.
The native wrapper must therefore prevalidate every token ID and reject any
non-exact element count.

The extractor currently creates a CPU llama model with mmap/lazy loading
before reading selected rows. The output buffer is bounded by 64 × 8192 F32
elements (2 MiB maximum); that is only the output geometry, not a peak-RSS
measurement. No native GGUF read, Redmi memory measurement, Termux test or
Android deployment is claimed here.

## Acceptance still required

- Core must call this helper from the actual Cognition.tap/receiver workflow
  after the native tokenizer and selected-row producer are wired.
- Fit a pair-specific TOKENWISE adapter only under explicit local consent, with
  source- and session-disjoint holdout.
- Test receiver-task utility against no-message, zero, shuffled-token, shuffled
  row, repeat, OOD and fresh-adapter controls; measure old-task retention and
  checkpoint/restart/rollback.
- Run the exact native model pair on Linux and then the authorized Redmi. CI,
  synthetic fixtures and native compile do not count as a phone proof.

Current classification: CODE_PRESENT / WIRED_SYNTHETIC_ONLY / NATIVE_GGUF_UNVERIFIED / REDMI_UNVERIFIED / B3_OFF.
