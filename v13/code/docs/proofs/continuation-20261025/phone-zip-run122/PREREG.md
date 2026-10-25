# Run122 — exact-head Termux source ZIP: actual persisted-stop CLI test

2026-10-25 UTC. Base: Run121 PR #152 head `10a290b62d954f264afa37e7e5d81787cc79eda4`, Run121 RED 40147274664 and GREEN 40147351197, 20/20 Linux software tests. Owner: **new Run122 workflow and Run122 proof files only**. No edits to Runtime, __main__, models, canon, tests or frozen experiment sources; do not overlap any active owner.

## Registered verification
The Run121 fix is proven on GitHub checkout but not in the distributable phone ZIP. Use existing source packager in phone-install mode on the **exact PR head** (not GitHub's synthetic merge ref). Independently check ZIP CRC, manifest, required launcher/setup/canon and new Run121 test, no private/model/database payload. Extract to a fresh directory and run real subprocess/SQLite `test_cli_standstill_run121`, inherited `test_phone_cli_run87`, `test_phone_operator_journey_run86`, `test_standstill` and `test_phone_halt` from **extracted bytes only**. Verify nonzero refusal under persisted human stop, then explicit release restores exact-copy output. Publish a short-lived source-only artifact only after all checks PASS; hash source ZIP and record exact head, artifact ID/digest separately. Preserve all failing attempts.

This is a Linux software/packaging proof, not Android installation, native model inference, actual JEPA learning, or general second-attempt utility. Original gates remain STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; DS2 H2 FAIL; V13 INCOMPLETE. No model downloads, privileged actions or paid provisioning.
