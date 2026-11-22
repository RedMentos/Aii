# Research & Perception handoff — RAW EYE source revocation atomicity

Date: 2026-11-22
Base: `gpt6/v13-private-remote-bridge-20261111` at `aed1d2b826290c95c70356b5d8b864b5ef382be4`
Branch: `research-perception/v14-vision-source-revocation-atomic-20261122`

## Reproduced defect / hypothesis

The new stored-image A5 bridge calls `vision.read_image`, then computes 17 visual summaries and asks A4 for a bounded context candidate. The existing image lab had no shared lock around IMAGE publication, reads, or `:image forget`. A concurrent forget could remove the image record, tombstone the source and unlink its blob while an A5 consumer was still processing the already-read image. Conversely, concurrent same-hash ingest and forget could interleave blob publication with the final live-refcount/unlink step.

## Change

- `vision.ingest`: serialize deduplication, blob publication, source-row insert and image-state publication under the Store RLock.
- `vision.read_image`: hold the same lock from live SourceRef check through blob read, hash verification, decode and crop.
- `vision.forget`: hold the same lock across image-state removal, source tombstone, live-refcount check and blob unlink.
- `consume_visual_source`: hold the Store RLock for the entire ephemeral A5/A4/admission construction. A forget therefore linearizes either before this operation (and the source is rejected) or after it (and the in-flight context has completed).

The Store uses a re-entrant lock, so nested Store transactions and read helpers remain valid. This is a per-process synchronization boundary; the Store's existing exclusive coordinator lock prevents a second Runtime process from opening the same home.

## Test

New barrier-controlled regression in `v13/code/tests/test_vision_a5_bridge.py` pauses RAW EYE feature extraction after the source read, starts a concurrent `:image forget`, asserts that revocation cannot finish while A5 is consuming the source, then releases the reader and verifies both the completed source-bound packet and rejection of later reads.

The existing workflow already runs this test file under Python 3.13 and 3.14 and compiles `vision.py` plus the adapter.

## Evidence boundary

- LOCAL_LINUX: full repository checkout unavailable in this execution container because GitHub DNS resolution fails. Exact committed test not run locally.
- LOCAL_LINUX isolated: lock-order/barrier behavior will be checked separately with a small CPython 3.13.5 harness; it is not the full Store/A5 integration.
- CI: pending on the exact new PR head until Actions completes.
- REDMI/TERMUX: NOT_RUN. No device connection, microphone/camera permission, model, weight, data or setting was changed.
- Runtime: the image adapter is still not called by normal Runtime; it is a source-bound candidate, not Android screen/camera support or visual semantic understanding.

## Next

Run exact-head RAW EAR/RAW EYE CI, then hand the tested image source-lifecycle contract to Core for normal Runtime invocation. Keep the existing text path and all V13 Canon goals unchanged.
