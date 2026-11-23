# WP-BP2b independent artifact-integrity review — CLOSED software evidence, 2026-10-27

**Scope:** independent child of native-runner branch exact `4d6e468f3a8ca30668063e85d6d8c06eb8f24f7a`; not production-integrated. Owner GPT-6 review branch `assistant/v13-bp2b-adapter-integrity-20261027`. Frozen source, model, tokenizer, 3 seeds and 4 arms unchanged. No native weights downloaded, no native inference/training, no authority change.

## Finding and fix

Confirmed defect: runner trusted `fit()['artifact']` and `fit()['hash']` without opening bytes. An absent, forged, symlinked or outside-attempt GGUF could produce a `COMPLETED` result. New `_verified_adapter_sha256` checks isolated trainer path, rejects `..` and symlinks (including child path segments), bounds regular-file size to 512 MiB, streams SHA256 with file stability checks, and requires the returned digest to match. Only then may the prediction phase start. Fake tests now create a small fake file and remain labeled `SOFTWARE_FAKE_TEST`. A failed check writes `FAILED.json` in phase `train`; original attempted outputs remain untouched.

## Original RED (preserved, not replaced)

- GitHub Actions run `40504249330`, exact commit `1e8557276210c1a84af4474e14c8f7cdc5b84e96`, runner blob `f2d51accc8c134847a44c7f61c938a328f91baab`.
- **19 tests, 4 expected FAIL**: missing artifact, wrong SHA256, outside path, symlink. Other 15 PASS; dry-run, compile and privacy exit 0.
- Original raw ZIP artifact ID `12733404382`; independently rehashed ZIP SHA256 `304450a9ee0b2a9fa241acbde4a64f1167f1bd7fcb95d8799e6c1a477c07ce80`; ZIP CRC PASS.

## GREEN (independently verified original raw ZIP)

- GitHub Actions run `40504405754`, exact commit `7a080ba848129abe7c5e6be697af617d4586be50`, runner blob `d302578671ea96fff9e34a4ba35a04a047f2f0ef`.
- **19/19 software tests PASS**, four dry-run plans exit 0, compileall exit 0, `public_repo_privacy_scan.py --base 4d6e468f3 --head HEAD` exit 0 / CLEAN.
- Original raw ZIP artifact ID `12734800294`; independently rehashed ZIP SHA256 `c3442be293976b10a7db98170070d627d31e67bb1ed14656d3c34a65f8faec3e`; ZIP CRC PASS.
- Original RED and GREEN ZIPs backed up privately to ChatGPT Library `/V13-Checkpoints/2026-10-27/BP2b-Adapter-Integrity/`, then materialized and compared byte-exact against the original downloaded ZIPs (both PASS). No anyone-writable Drive destination used.

## Gate and handoff

**Evidence level: software/synthetic only**. `STEP2 UTILITY_FAIL`, `B3 L1 FAIL`, `BJ1_NO_SIGNAL`, `jepa_weight=0`, Redmi unmeasured, `canonical_architecture_complete=false`, `user_full_scope_complete=false` unchanged. No Age, route, tool or learning promotion.

Next command after review/integration: `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_native_runner tests.test_bp2b_transfer_score`. Before any real native run: inspect current heavy owner, download exact pinned model only into isolated permitted cache, rerun full master/tokenizer preflight, verify `BodyJepaTrainer` export and Q4 comparison independently. This package does not prove BP2b improves learned utility or leakage.

Potential remaining review: tokenizer files could change between preflight and trainer load; the current guard verifies the exported adapter, not all source files after execution.
