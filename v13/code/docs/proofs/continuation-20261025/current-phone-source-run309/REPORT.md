# Run309 — current-chain source-only Termux ZIP with Run304–308: verified and privately backed up

UTC 2026-10-25. Draft PR307, base verified Run308 checkpoint `3d7343dbedc6cd829df3c38df853f3aad0579217`. Preregistration commit `1b0dd2905a227dfe4545173d1283037a952e0480`, dedicated workflow `1c4a5c6ac95207a0704de7cd680460efc6e080be`. No production source edits in this package.

## Actual exact-source evidence
- GitHub Actions `40206524308`, job `121208527418`: **PASS**; official public privacy scan CLEAN. Exact packaged source `1c4a5c6ac95207a0704de7cd680460efc6e080be`. Canon SHA256 unchanged `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`.
- Canonical `scripts/package_source.py --phone-install` produced `V13-Phone-Run309.zip`: **12,946,925 bytes**, SHA256 `116cbb3dc333edc6a1ecace1886a8ee7651de3e24ed5f027bc97a79266b6c681`; 1021 ZIP members including manifest, 1020 source files, 29,295,835 uncompressed bytes. Manifest SHA256 `d3ea2c74b6d85c28e926a14c759ac1abbc4021190bf31c282688dd86750a99c4`.
- Independent verifier: CRC PASS, all member SHA256 PASS, checkout byte parity PASS, forbidden private/model payloads excluded, native model inference FALSE, Redmi measured FALSE.
- ZIP extracted into isolated Linux temp, `V13_SOURCE_ONLY_DIAGNOSTIC=1` setup PASS, Age-0 CLI initialized, truthful `NO_NATIVE_MODEL / NO_REDMi / NO_JEPA_PROOF`. Extracted-source actual SQLite/phone tests **25/25 PASS**: Run302 learning status, Run304 backup source closure, Run306 WorldModel source-disjoint holdout, Run307 Sleep A exact retention, Run308 Attention durable receipt, phone operator/CLI. Separate independent local extraction and same 25 tests also PASS.
- Raw GitHub artifact `12603119603`, outer ZIP SHA256 `4f6213f4238a29f5bc653de3e3b8b6cbb9706a2b6df6f490bc6fc72e0c714943`; all required package/verify/extract/privacy exit codes 0. Downloaded, original outer/inner hashes checked, raw SHA256SUMS verified, ZIP CRC checked.
- Private persistent Library backups `/V13-Inquisition/Proofs/Run309/V13-Phone-Run309.zip` and `/V13-Inquisition/Proofs/Run309/V13-Run309-Current-Phone-Source-Artifacts.zip` both uploaded, then **read back byte-for-byte** with SHA256 parity. Rejected anyone-writable Drive destination not used.

## Scope and next
This is **source-only Linux software and archive integrity**. Normal Termux model/native setup is not performed by source-only diagnostic. No native model inference, Android/Redmi thermal/RSS/battery measurement or Body-JEPA utility proof. STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, V13 `INCOMPLETE` remain. PR307 is review-scoped; main is older.

Next independent integration package: run the **entire** test suite on this new chain with pinned CPU dependencies and exact frozen fixture staging, retain failures and compare to baseline `40202886433` (2833 tests, 2 failures, 36 errors). Heavy native/model jobs serialized with existing concurrency group; do not modify frozen source hashes or claim suite PASS if errors remain. Then resume substantive Canon work outside completed packages.
