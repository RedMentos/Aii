# Run622 — current review-chain source-only phone ZIP integration

2026-10-26. Review-only child of Run621 PR616 at exact base `405c7d8be42d34b98b80a83e48c79a49cc20aa27`. New workflow builds `V13-Phone-Run622.zip` from **exact GitHub checked-out head** with existing package/verification tools and no model download, then runs source-only extracted SQLite tests across Run619/620/621, Run618 synthetic replay, existing prompts and package tests. Pull-request trigger is included to permit exact run/head inspection. **Exact-current Actions run and ZIP artifact pending**, no success claim until observed.

## Independently executed local prerequisite proof (not current head)

From original Run601 phone source ZIP `fdcbefc129b28b085fcfa84a4bc3ee44cce74b62`, overlaid source-identical Run619/620/621 modules/tests and original Run618 synthetic cohort, built a source-only Termux ZIP using unchanged packager blob `06167e0bcb82b36cb08841cd31b9618c4ba0926e` and verifier blob `880dbd2cebb0aac5c7b37e25a5ca8487b796cfa1`. Independent verifier reported CRC PASS, all member hashes PASS, source byte parity PASS, negative gates unchanged; local ZIP SHA256 `6c4bd35d2c7ff84bcef55ba52b129271ce6ddac9fd320de72ac6404fbd452e1b`. Existing packager tests **8/8 PASS**, verifier tests **7/7 PASS**.

Extracted source-only ZIP + original Run614 SHA-closed native states for offline Run621 test: **41/41 SQLite/source-only tests PASS**, including `:language` restart, B2 cosine precision, original Run618 synthetic replay and NO_GAIN diagonal readout. Run618 registered cohort is intentionally **not included** in the portable phone ZIP; for the 41/41 integration run, its original verified `RUN618_COHORT.json` was copied into the extracted test fixture directory after extraction. Without that test-only fixture, two Run618 tests correctly SKIP; the source ZIP itself was not modified.

**Scope:** This local ZIP uses an older Run601 base and does **not** establish full exact-current GitHub branch packaging or Android/Redmi execution. No native model inference, no new body training, no model weights bundled, no semantic utility gate promotion. STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi UNMEASURED; V13 INCOMPLETE.

## Next command

Verify exact Run622 GitHub Actions pull-request workflow run/head, raw PACK/VERIFY/NATIVE_DOWNLOAD/TEST/PRIVACY exit codes, ZIP manifest, original native source hashes and uploaded artifact. If RED, retain raw and fix on a child; if GREEN, persist ZIP and raw private checkpoint and continue next distinct canonical package. Production main remains unchanged.
