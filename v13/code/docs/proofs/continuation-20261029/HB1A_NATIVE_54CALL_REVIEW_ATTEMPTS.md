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

## Attempt 2 — GREEN Linux-native diagnostic, independently checked

- Exact execution HEAD `f7db8dcfa3297061c1cdc9d234f3097c6a417e96`, Actions run `40836705747` **SUCCESS**; original artifact `12881321580`, ZIP SHA256 `7d180436ab64165f867a80902add7b23f8dae19cbbfd72b8b266ac48c47b4552`.
- Independently downloaded original ZIP: CRC CLEAN, **50/50 SHA256SUMS matched**; all 14 stage exits = 0, source/parent artifact checks GREEN, 16 focused tests PASS, privacy CLEAN, no model-weight bytes in artifact.
- **Real Linux x86_64 model calls:** B1_DETAIL 18, B2_GIST 6, C3_LANGUAGE 30 = **54/54 FINAL**. All three pinned GGUF hashes and llama-server SHA unchanged before/after, process reaped, Age0 RECORD_ONLY, no training/adapter activation.
- Raw SHA256 `abbcacec1217e51dfc592d2e981db9597162b475ca01886151fa99c39a1df7e1`; score SHA256 `b7ba7c038d420cba7bb78dc62cba0b66ed7d41b50c8f5e7b4f9f85e3697c3c44`. Private Library backup `/V13/RawEvidence/HB1A_40836705747_54call_linux_native_exact_head_raw.zip` rematerialized and byte-verified against ZIP SHA.
- **Diagnostic exact actions out of 6 per arm:** C3-only **2**, both-exact **0**, both-native **2**, single-body-native **2**, shuffled-native **2**. All 24 generated-offer-arm C3 outputs were `NONE`; both-exact produced `B` twice and `NONE` four times. Thus no observed B1/B2-generated-offer utility improvement on this small public synthetic cohort, and no demonstrated foreign-source rejection. Do not rescore original data or promote gates.
- Detailed hash-bound result: `HB1A_NATIVE_54CALL_REVIEW_RESULT.json`. **No Redmi measurement, no independent 150-row holdout, no STEP2/B3/Body-JEPA/LP3/whole-system promotion.**

## Next substantive package

Source-only preregistered 150-row independent held-out model-native complementarity/receiver diagnostic with genuine oracle headroom, plus a separate C3 receiver-format/training ablation if evidence supports it. Avoid altering the original six-row registered cohort or its negative score. The native runner is now idle; no heavy process ownership remains from this workflow.
