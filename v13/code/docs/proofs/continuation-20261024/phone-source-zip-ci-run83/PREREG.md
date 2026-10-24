# Run83 prereg — verified source-only Termux ZIP CI artifact

2026-10-24. Base Run82 PR115 `de86bef43aa0bf53f5b145cd1d86aa1fe414530f`.
Owner: `.github/workflows/v13-focused-proof.yml` release artifact steps and new Run83 evidence only. No runtime/model/canon/acceptance changes. First-party `actions/upload-artifact` pinned to official v4.6.2 commit `ea165f8d65b6e75b540449e92b4886f43607fa02` (verified GitHub tag).

Problem: user needs a runnable, verifiable Termux source ZIP across checkpoints; the source packager exists (`scripts/package_source.py --phone-install`) but the GitHub CI does not publish its output. A successful source-only CI package is not a full installed model, native or Redmi proof.

Predeclared steps after the existing Linux regression suite and privacy scan: run `python scripts/package_source.py --root . --out "$RUNNER_TEMP/V13-Phone-Run83.zip" --phone-install`, require its closed per-file SHA-256 manifest and archive CRC verification, independent `unzip -tqq`, print SHA-256/size, and upload the immutable ZIP as a GitHub Actions artifact with retention 30 days. ZIP must include `V13-Phone/setup.sh`, `V13-Phone/STARTEN.sh`, canonical `docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`, and `WORKSPACE_FILES.json`; reject if missing. Source packager excludes user data, credentials, model weights and SQLite. Artifact upload is read-only to repo and is not a backup substitute for verified GitHub source commits.

Do not download models, run native inference, claim phone-measured results or promote STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE. Preserve failed packaging attempts and logs. If artifact upload unavailable, record exact CI failure and keep code checkpoint.
