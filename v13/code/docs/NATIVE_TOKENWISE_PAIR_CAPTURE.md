# Core native tokenwise pair capture

## Runtime path

A local operator can arm and execute one source-bound pair capture:

- ':callosum arm-tokenwise-pair B1_DETAIL C3_LANGUAGE --last-source --confirm'
- ':callosum native-tokenwise-pair B1_DETAIL C3_LANGUAGE --last-source --confirm'
- ':callosum revoke-tokenwise-pair'

The approval is local-TTY-only, one-shot, session/event/generation/source-bound and tied to the exact installed sender and receiver model files. It uses the existing exclusive Runtime lease, queue-empty check, managed-process census, cancellation path and bounded deadline. It is a distinct TOKENWISE_PAIR_CAPTURE approval kind; it cannot consume a native-receiver or input-table-only approval.

The sender side calls the existing Cognition.tap() and then Cognition.read_tap(). This creates the ordinary source-bound LatentTapPacket and persists its numeric feature blob locally under data/blobs/. The receiver side obtains add_special=false, with_pieces=true tokenization from its exact role runner, unloads that runner, and invokes the pinned llama_model_get_tok_embd_rows extractor. The complete extractor output object is passed to the Perception-owned build_native_tokenwise_pair_record() helper, which calls the #2506 extractor-output manifest bridge and aligns different tokenizers by UTF-8 byte-piece overlap.

Tokenizer identity is bound as llama-server:b10964;gguf:<model-sha256>: the tokenizer is embedded in the immutable GGUF and the runner implementation is pinned separately. Sender final-RMSNorm rows, receiver input-embedding rows and event-pooled LATENT_PREFIX_V1 are different spaces and must never be substituted for one another.

## Persistence and authority

- The existing sender LatentTapPacket and its feature blob are persisted locally by Cognition.tap(); the audit reports this explicitly.
- Receiver input rows, aligned pair vectors and the PAIRED_DIAGNOSTIC record are not persisted.
- Only a bounded digest/count/coverage/source/model audit is written to Store; no source text, token pieces, token IDs or vectors enter that audit.
- No receiver inference, production route, semantic-use proof, model/weight change, adapter persistence, training authority or B3 enablement occurs.
- fit_native_tokenwise_pair_cohort() is an in-memory wrapper over the #2508 schema-v4 fitter. It requires the fitter's whole-session split (at least two sessions per side, no overlap) and returns only an in-memory PCA+ridge candidate. It does not save or activate the adapter.

## Acceptance still open

1. Build/install the pinned native extractor binary through the release packaging path; this PR's native workflow compile/cross-compile is not an installed-phone binary receipt.
2. Run the one-shot command only after explicit local user approval on an actual supported device.
3. Collect at least two independent sessions for train and two for holdout; pass the resulting approved in-memory records to the schema-v4 fitter.
4. Test receiver-task utility against exact-message, no-message, zero, shuffled, repeated and OOD controls, then measure retention/restart/rollback.
5. Only after those gates may a separate reviewed native receiver consumer be considered. Production B3 remains OFF.

No GGUF was read in this development run, no model or device data was changed, and Redmi remains REDMI_UNVERIFIED.
