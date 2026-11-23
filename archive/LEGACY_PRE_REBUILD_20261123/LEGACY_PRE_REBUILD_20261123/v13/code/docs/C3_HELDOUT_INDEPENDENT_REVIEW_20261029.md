# Independent C3 heldout raw audit (2026-10-29)

Review-only, **not** a production merge or new native run. Source PR #1138 (branch `codex/v13-c3-native-heldout-20261029-auto10x`), Actions `40940312940`, artifact `12925808672`.

The original downloaded ZIP has SHA256 `458629d91f41d7aa2fd371d070a8b434e1281ec82ccb29851b3250b264d87ca7`, valid ZIP CRC and **32/32** inner `SHA256SUMS`. Each of six native stdout blobs matches its report SHA256, each exact generated-only string hashes to the report's `generated_sha256`, and a separate read-only implementation of the frozen amount/abstention oracle reproduced all six reported judgments.

| Case | Generated-only output | Frozen oracle |
| --- | --- | --- |
| en_present | `160 euros` | PASS |
| en_absent | `UNKNOWN` | PASS |
| en_revised | `The current budget is 75 euros.` | PASS |
| de_present | `Betrag: 160 Euro / Waehrung: 0` | FAIL: unsupported extra 0 |
| de_absent | `UNKREID` | FAIL: not exact UNBEKANNT |
| de_revised | `Betrag: 75 Euro / Wehrung: 50 Euro` | FAIL: unsupported extra 50 |

Independent result: **3/6 total, English 3/3, German 0/3**. All six native calls are marked `native_smoke_pass=true` and scorable; this is not a parser failure. Pinned C3 GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, pinned llama.cpp tar SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`; registered cohort SHA256 `237d2ef0391a341a1001efac272512826fd0f127c3fa8c8bb4cd99a7f8c3beb4` unchanged.

Private Library original ZIP backup: `/V13-Checkpoints/2026-10-29/Automation10-Independent-C3-Audit/C3_NATIVE_HELDOUT_40940312940_sha458629d9.zip`. No public private-user data.

**Interpretation:** bounded **Linux-native C3-only** fixed-oracle evidence. German reliability failure is real in this small cohort. No B1/B2, JEF/C2, Memory consumer, phone, generalizable bilingual accuracy, learning gain, or end-to-end V13 proof. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, Redmi UNMEASURED, V13 INCOMPLETE. Preserve both successes and failures; do not change the registered cohort or score after observing outputs.
