# Run95 phone ZIP workflow staged — 2026-10-31

Owner GPT-6 Auto11, draft review-only PR #1461 child of Run94 exact parent `8d3d4d28313394de7ec023fcd29497d56bfd3b81`. Prereg `6a11da8e94db5324870c518173bad347c5f3690e` remotely verified before workflow. Existing packager, release auditor, STARTEN.sh, Canon/model/source pins unchanged. New workflow `.github/workflows/v13-run95-phone-source-zip.yml` HEAD `055e49de80be98eda587310af85e613580247121` (verified remote blob `e946f40f68c7ba5b637bcf0a4fbc4bf6d0ff252b`).

The workflow is marker-gated on absent `v13/code/docs/RUN95_PHONE_ZIP_TRIGGER.txt`; **NOT TRIGGERED**. It requires two byte-identical independently packed archives and creates immutable `V13-Redmi-Install-Run95.zip` using existing `package_source.py --phone-install`, verifies ZIP CRC/manifest/source hashes/no symlinks, extracts into scratch, runs real model-free source-handoff/native-firing/Run34/37/83/90/package tests, rechecks original extracted bytes, checks bash syntax of STARTEN/setup/TESTEN/TESTEN_STEP2, and saves source ZIP + raw logs/exit receipts (extracted scratch stays outside artifact directory). No native model, no Redmi or user data, no promotion. Privacy/diff checks included.

**Launch prerequisite:** Run94 original native-ZIP unfiltered full-suite Actions `41200093567` must be terminal GREEN with downloaded original ZIP CRC/SHA256/inner manifest, all stage exits and no unexpected tests. If RED, preserve and repair before package acceptance. Run87 native child Actions `41200115473` owns heavy native; Run95 packaging is model-free and may run independently.

**Next exact command:** GET `https://api.github.com/repos/RedMentos/Aii/actions/runs/41200093567`; after GREEN + raw audit, create `v13/code/docs/RUN95_PHONE_ZIP_TRIGGER.txt` on PR #1461 branch with original artifact ID/SHA and negative gates; verify remote trigger, inspect Actions, download original ZIP, verify and back up privately byte-identical. Keep all failures and skips explicit.

Gates: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight0; Redmi UNMEASURED; whole V13 INCOMPLETE.
