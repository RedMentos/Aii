# QA — source-lifecycle builder rebind for promotion/forget serialization

Date: 2026-11-22  
Stacked base: Boss Store-generation/source-forget branch, head 1dfdd856daa3c16679f5466e168dadf43a384f29  
Status: candidate fix; exact Python 3.13/3.14 workflow pending

## Reproduced failure

On #2355 exact merge head e9cf9529e21494ac03ea83578b1a01bc1923df03, workflow run 45044319345, Python 3.14 job 137275483658 failed:

- 17 passed, 5 subtests passed, 1 failed
- test: test_v14_store_source_blob_serialization.py::test_staged_store_read_open_is_linearized_with_revocation
- failure: source_lifecycle_lock_integration_candidate.py rejected the changed Store source at its exact SHA pin.

## Exact source hashes (SHA-256)

- Store.py at #2355: bc7ab8edfd26bf0222ebcccbf57c95612f3fe305646eb46571b35b6f72942bd1
- Memory.py at #2355: b205901627af857fc4465204ebc12518d9955d2d62b8ce20f1a83731ef560799
- archive_reader_guard_integration_candidate.py after its Store pin update: 313f2dc078366fa851c3ef76b425fb800e7369c73ed5cb69ea93f96cc95f0596

All other existing source pins in the outer source-lifecycle builder were checked against the #2355 branch and matched.

## Fix

- Rebound the nested archive guard integration builder's Store SHA to the exact #2355 Store source.
- Rebound the outer source-lifecycle builder's Store and Memory SHA pins.
- Updated the outer builder's GUARD_SCRIPT_SHA to the exact new nested builder bytes.
- Kept the old Store SHA as a separate OLD_STORE_SHA for the guard/stream candidate replacements, because those downstream candidates still contain the pre-composition Store pin.
- Updated MEMORY_OLD to the exact #2355 Memory cleanup block, preserving the Store RLock/JEPA guard while replacing only the final blob cleanup with source_lifecycle_candidate.cleanup_unreferenced.
- Verified the Store source-publication, recovery, event-publication and read_source replacement anchors each occur exactly once.

## Proof boundary

The original failing CI result is a confirmed regression. This candidate rebind has not yet been run on the full A5/source-lifecycle workflow; the next exact-head CI run must prove that the builder composes successfully and that the staged Store read/revoke test passes on Python 3.13 and 3.14. No local Aii checkout, full Python test, native Linux integration, Redmi or Android proof is claimed. The change is test-builder-only; it does not activate source lifecycle in the installed runtime or alter weights, memories, models or phone data.
