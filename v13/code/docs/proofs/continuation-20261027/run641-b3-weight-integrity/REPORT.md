# Run641 — exact B3 weight-byte validity, source-bound RED→GREEN (2026-10-27)

**Parent:** Run640 PR #636 exact source `0928f3e06855efd4596f7322a1574d9f30fea3e8`. **Review branch only**; no main integration or authority promotion. Owner: GPT-6 Run641, only `bodyport.py`, `test_bodyport.py`, this proof and its CI.

## Actual change
`Ports.bridge_valid` no longer trusts an otherwise correct JSON manifest by itself. It resolves exact live sender/receiver model revisions and bridge keys, loads the matching B3 NPZ through existing `Bridge.load`, validates its array digest against the loaded manifest, and only then compares direction and both exact bridge keys. Missing, truncated, modified and malformed artifacts fail closed. A real tiny saved bridge remains valid. Legacy revision-only manifests remain invalid. All existing BodySwap/port/bridge tests are preserved.

## Original failures (retained, not relabeled)
- Prereg `5098eef8082b1ad803aae58c9e702fec57523851` before tests/implementation.
- **RED** Actions `40436511959`, exact head `52a4f0204caf3df2fde3d05ce7dcfd941fa822a2`: 55 tests, **3 expected FAIL** (missing NPZ, modified array, corrupt NPZ incorrectly accepted), compile/deps/privacy PASS. Original ZIP SHA256 `4e9a3c59ded2265ee7f2da60b86e0a8f0273ebfd335cd672f576b196b82cebb9`, 12/12 inner hashes, CRC PASS, private Library byte-identical backup.
- First fix **RED** Actions `40436633366`, head `735bd1d19fdadb45b9534a693543de0739cc416e`: 55 tests, 1 ERROR for malformed JSON list manifest (AttributeError in legacy Bridge.load). Original ZIP SHA256 `ac944b1b59575beb02a5c833b1521a33be484fcfc44f25e3b60e356864dfecee`, CRC PASS, private Library archive. Prospective amendment `8aca9114d31b8422bd5cae44b15609d25661fb38` before narrow fix.

## Exact source GREEN
- Actions **`40436747038`**, exact tested commit `8336e5085b0c9f33541ac720b1ba13435ea1f2ef`, `python -m unittest -v tests.test_bodyport tests.test_bodies tests.test_b3bridge tests.test_body_training_port tests.test_body_train_port_paths_run90 tests.test_body_train_port_schema_run91`: **55/55 PASS**, compile PASS, isolated NumPy 2.3.5 deps PASS, privacy `0928f3e06..HEAD: CLEAN`.
- Original raw ZIP SHA256 **`7aee519df7879758350c15a3d716ac8fb9de1602abdd2e14d5a1ba1d1d3fa451`**, artifact ID `12704641846`; CRC PASS, 12/12 internal SHA256 PASS, `RUN641_HEAD.txt` equals exact commit, source SHA manifest present. Private Library `/V13-Checkpoints/2026-10-27/Run641/Run641-source55-GREEN-40436747038.zip` re-materialized and byte-compared to original: identical.
- Remote source blob IDs: `bodyport.py=0f5f5d2a41e3fc4fbb1d008803723df783f29248`; `test_bodyport.py=a42bbe02f2f1a0467033f71b5c8a86a86d1bb23e`. Canon SHA256 unchanged `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`.

## Limits, blockers and next
Software-only Linux CI with tiny synthetic NumPy bridge weights; not a learned real B1/B2 latent bridge, no native receiver-injection path, no Redmi execution, no L1 utility. The historical B3 producer still lacks an integrated exact-live-identity bound training/publish path; Run641 does not fabricate one. The existing negative gates remain **STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi unmeasured; V13 incomplete**. No production weights, age/approval settings, registered model/cohort/source hashes or authority changed.

**Next command:** inspect the source-bound Run641 GREEN artifact and PR, then continue a separate canonical functional package (C3 learned-answer locality/retention or B3 trained sender/receiver data path) with its own prospective cohort and controls; do not merge to main directly. Owner of future native heavy jobs must be checked first.