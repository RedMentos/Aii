# Run11 native single-turn bounded raw — verified checkpoint 2026-10-28

Owner: Codex, review-only child PR #840 of #839, no main merge. Current source head before this note: `dbbd5e0e90abc661933e0026bc334fd03ac01bbc`. Original prereg `ef6f091ecd83027fce799b75d1c8c04bdbf1370f`. Original C3/B1/B2 catalog/manager blobs, model SHA256, runner SHA256 and frozen source/seed unchanged.

## Preserved original RED, independently inspected

#838 native Linux run 40629227523 at source `c0260321fb7a26c3c7e6cd867a1879fe7ce164a0`; artifact 12790289704 ZIP SHA256 `b922aa4c9356e0f8d2be3b32c9d6eb14ab13c0c8d9cf9b516ae91e564d490525`, CRC valid, internal raw hashes matched. Pinned C3 did generate a reply but default interactive `llama-cli` emitted **962086943 stdout bytes** SHA256 `8fe6aa49858d358b9ce60bfefe48ee0e6512ed0a0cbf54a75d565f10689e9020`, timed out after 182.647s, native_exit_code124, smoke RED. Not a success, not overwritten.

## Fixed candidate and actual GREEN

Shared `scripts/native_smoke_io_20261028.py`: `--single-turn` mandatory, stdout/stderr direct raw regular files each limited by Linux RLIMIT_FSIZE to 1 MiB, explicit cap/timeout metadata, byte SHA256, reject banner-only output lacking generation marker, no overwrite. Both C3 and B1/B2 smoke scripts call it, model/runner pins unchanged.

Focused workflow 40630358554 at `d477f5830aeffa682bf9d89076a4b616b519223b`: **13/13 PASS**, compile0, privacy CLEAN, diff0. Artifact 12790359736 ZIP SHA256 `a3ee391c04ae7e1484a39e0584cbd2e5819df0f6236c288932c1d4f20912f63f`, CRC and 9 internal SHA256SUMS verified. Earlier shallow-checkout privacy failure is retained as CI failure 40630280166 and fixed with fetch-depth0.

**Actual pinned C3 Linux native** workflow 40630449102 at `f14ff2d998df5f43e32e666640107f9ab537689d`: SUCCESS, artifact 12791207583 ZIP SHA256 `064425a7cf1184c145a83e0248c5b42fdcccf5cccc67b8716376d9338b8b8573`, CRC valid and **17/17** internal SHA256SUMS verified. `native/REPORT.json`: C3 model SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`; runner tar SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`; actual llama-cli SHA256 `3acf625ff44f1dc28799e7e036519207b5564191d6243371bfae086b3911ed71`. Prompt `Hello.`, 12 tokens, 2 threads, temperature0; native_exit_code0, 0.617s native elapsed (excludes download), `native_smoke_pass=true`, generation marker true, `raw_capture_complete=true`, `raw_output_capped=false`, stdout **1008 bytes** SHA256 `b287af49a4da7b5172bb5d23a13032b830b1c0deb109f8bb17f3aeaed60b9df8`, stderr0. Actual raw contains one response and `Exiting...`, not repeated prompts. CI guards, native, report check, privacy, diff all exit0. This is a **C3-only Linux-native smoke**, not C2/JEF, B1/B2, semantic quality, learning, Redmi or whole-system evidence.

## Next independent package / prerequisites

After C3 completion, run the already preregistered distinct B1/B2 Linux native serial smoke from #839 with this fixed helper, on a new review child branch, **only one heavy native job at a time**. Before launch check active heavy owners; retain source/model/runner hashes and both raw role outputs. Next command after checkout: `PYTHONPATH=v13/code python3 v13/code/scripts/current_b1b2_native_linux_smoke_20261028.py --scratch-home <fresh> --evidence-dir <fresh>`. Full Linux software suite and independent review on PR #840 remain open.

Negative gates: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 heldout FAIL; jepa_weight=0; Age0 RECORD_ONLY; canonical_architecture_complete=false; user_full_scope_complete=false. No private user/model bytes in public Git; only metadata and public fixed prompt raw. Remaining platform budget UNKNOWN.
