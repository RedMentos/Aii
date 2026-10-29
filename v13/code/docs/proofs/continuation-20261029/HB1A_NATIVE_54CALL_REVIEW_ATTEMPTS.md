# HB1a 54-call Linux-native review — immutable attempt ledger (2026-10-29)

Owner: GPT-6 isolated review branch `codex/v13-hb1a-native-54call-review-20261029`. Parent PR #1053 exact `15fc02a214380d178ff857ee50c2a11b6640704f`, prereg PR #1052 original blob `9d6652e99ac9aa0de7898f15eeb8a54d598c49e6`. No Canon, registered cohort, model/runner pin or runtime changes. No production merge.

## Attempt 1 — RED, retained

- Exact workflow commit: `6cc70df41a4857db05a2a660933391fb7905c2ae`
- GitHub Actions run: `40836608947` (completed **failure**, 2026-10-29 07:37 UTC).
- Original raw artifact: `12881141167`, ZIP SHA256 `c928799624fec5b16b249089dcbdfecd1f61a99cdc180aa5bfa04217dd0ac172`; retained in GitHub Actions, no model weights.
- Independent artifact download: ZIP CRC CLEAN, **47/47 internal SHA256SUMS matched**, stage exits SOURCE/PARENT_SOURCE_DOWNLOAD/PARENT_EXECUTOR_DOWNLOAD/PARENT_VERIFY/RESOURCE/DEPS/COMPILE/FOCUSED/PRIVACY/DIFF = 0; INSTALL = 1, NATIVE/VERIFY = SKIPPED_RED. Original ZIP SHA256 matched GitHub artifact digest. Permitted private Library backup `/V13/RawEvidence/HB1A_40836608947_install_home_missing_RED.zip` uploaded and rematerialized, SHA256 byte-identical.
- All earlier source/parent/resource/dependency/focused stages reached the install step. **INSTALL RED before model download/inference**: `FileNotFoundError` at `shutil.disk_usage(home)` in `hb1a_native_executor.admit` because workflow had not created its fresh isolated `$home` directory. This is an orchestration prerequisite, not a native model failure. Do not count any real B1/B2/C3 call or claim model compatibility from this attempt.
- Corrective workflow-only commit: `f7db8dcfa3297061c1cdc9d234f3097c6a417e96`; creates `$home` before invoking the unchanged pinned executor. No force-push, no source-pin alteration.

## Attempt 2 — pending independent verification

- GitHub Actions run `40836705747`, exact head `f7db8dcfa3297061c1cdc9d234f3097c6a417e96`.
- Verify all stage exits, SHA256SUMS and original closed raw, source/model/runner hashes and native process teardown. If RED, retain artifact and correct only the observed failure, without rewriting attempt 1.
- Even if GREEN: six public synthetic tasks only, Linux x86_64, no Redmi and no acceptance gate promotion.

## Negative gates

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; V13 INCOMPLETE. Original Canon, all cohort/seed/model/source hashes and failed evidence unchanged.

## Next command

Inspect exact run and its original raw: `gh run view 40836705747 --repo RedMentos/Aii --json status,conclusion,headSha`; after completion `gh run download 40836705747 --repo RedMentos/Aii -D <fresh-private-review-dir>`, independently check every `SHA256SUMS.txt` entry and all stage exit codes. No user/private data in public artifacts.
