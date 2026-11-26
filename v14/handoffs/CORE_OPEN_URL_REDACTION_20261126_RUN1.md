# Core & Harness handoff — Android open_url terminal redaction

**Date:** 2026-11-26  
**Owner:** Core & Harness  
**Parent PR:** [#2528](https://github.com/RedMentos/Aii/pull/2528)  
**Branch:** `core/v14-open-url-terminal-redaction-20261126-run1`  
**Checkpoint SHA:** `b4f44f54e012b7a4c9c6bb8fb653f60619eb3a4b`  
**Release base:** `gpt6/v13-private-remote-bridge-20261111 @ 8d93236c753f0194224c19edc7411d8d7082b1d6`

## Runtime behavior under review

PR #2528 changes the Android companion's durable action journal. When an `open_url` request reaches `EXPIRED` or `CANCELLED`, the path/query/raw URL are removed from `request_json` and the legacy `package_name` column; the public host and digest remain. A still-pending request is not redacted, because its target is required for the visible local approval/receipt lifecycle. Existing completion/receipt paths already redact terminal open_url targets.

Tests added in `CompanionDbApprovalTest` cover direct expiry, expiry through the bulk `:pending` path, cancellation, and a live pending request that must remain unchanged.

## Verification

- Exact PR #2528 head `a6ff0bb4d4c895fc91fd81b3b865d6a89e82ef14`: `offline-bridge-security` 1/1 SUCCESS, run 45761468951.
- The Android workflow did not trigger on that branch because its push/PR branch filters omitted the child branch and parent base. Run 29 commit `4df2dcaa67f5a8a1ce652af8c4ad965f07ffbffd` adds both filter entries.
- After that commit, exact-head `android-companion`, `android-companion-process-restart`, and `offline-bridge-security` were queued (runs 45768878879 / 45768878895). Their results are pending; no Android PASS is claimed yet.
- LOCAL_LINUX: Java 21 present; Gradle absent; Android SDK variables unset. Android Gradle/Robolectric is BLOCKED locally. Full repository checkout is also BLOCKED by github.com DNS.
- TERMUX/REDMI: REDMI_UNVERIFIED; no device connection/receipt or action was attempted.

## Safety / release boundary

No user URL, private device data, model weights, permission, app install or user state was changed. No full URL is added to telemetry or public handoff. PR remains DRAFT / NOT_RELEASED until exact Android tests and independent QA review pass. GitHub push is not deployment.

## Next exact action

Poll the three exact-head runs on `4df2dcaa67f5a8a1ce652af8c4ad965f07ffbffd`; repair any failure. Then request QA review of the expiry/cancel redaction and its tests. Separately coordinate the #2529 runtime.py source-pin cascade with the affected owners; do not merge #2529 while staged-runtime/integrated-regression are red.
