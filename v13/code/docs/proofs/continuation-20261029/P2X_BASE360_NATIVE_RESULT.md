# P2X frozen C3 QAD base-only 360-call Linux-native validation result — 2026-10-29

Owner GPT-6 isolated PR #1078, **not production merged**, original prereg `P2X_BASE360_NATIVE_PREREG.md` commit `94ba9cdda1f685665bca2bc6b2069eb7aaf3b904` preceded source/model calls. No adapter loaded, no training, no P0X holdout use.

## Original RED retained
First native [40856847507](https://github.com/RedMentos/Aii/actions/runs/40856847507), head `7ef8240e74239327054320a4f2f28245967ef1e4`, original ZIP SHA256 `590f5d8ba8efe9c76635e67046999babefad76263210c8f7e0eb3b1883dab703`, CRC CLEAN, 29/29 SHA256SUMS. Source/resource/cohort/deps/13 focused tests/install/privacy/diff all passed; native preflight RED **before any model call** because release archive SHA `9abf88...` was compared to extracted binary SHA `79e312...`. Original raw privately backed up byte-identical. Prospective `P2X_BASE360_ARCHIVE_BINARY_HASH_ADDENDUM.md` committed **before** repair; unchanged registered archive SHA preserved, distinct extracted executable SHA verified. Repaired source-only [40857147626](https://github.com/RedMentos/Aii/actions/runs/40857147626) GREEN, **15/15 tests**, 9/9 SHA256SUMS, 4/4 exits, ZIP SHA256 `5212bf85c3c7fe08a9bf72778e860dc24124752773cf37b18893176fd863d93e`, privacy CLEAN; original source raw privately backed up byte-identical.

## Actual native result — independently audited
- Pinned [Actions 40857239739](https://github.com/RedMentos/Aii/actions/runs/40857239739), exact workflow head `80c0cf5af8eb56d901cba9d2a7ac4f40c57b4eed`, completed **GREEN execution, NEGATIVE utility**.
- Original ZIP SHA256 **`43e8dcc71370cf17355d4cd0bbc4f9aaa1378ead648a1de3425edf333b082d93`**, CRC CLEAN, **34/34 SHA256SUMS**, **13/13 stage exits zero**, privacy/diff CLEAN, frozen P2X 3/3 file SHA and source blobs all matched. Original ZIP privately backed up and byte-identical at `/V13/RawEvidence/2026-10-29/P2X/base360_native_GREEN_40857239739_sha43e8dcc7.zip`.
- Exact C3 QAD GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`; llama.cpp b10964 **release archive** SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`, extracted `llama-server` **binary** SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`; both separately verified before/after. `adapter_sha256=null`, no active adapter/memory mirror, age authority0, no weight updates, jepa_weight0.
- **360/360 real native model calls** on 72 distinct held-out IDs × five frozen source arms, seed13, 48 output tokens max, schema-constrained JSON, unchanged single-user-message input SHA per row, no hidden oracle, all FINAL, process reaped. Original `RAW.json` SHA256 `0d554d20cbcd320a799558d2dc6c0f2f3c58bc7feeaaade7d6452f88228e2a8f`; `SCORE.json` SHA256 `2a20ec5fcdf19d323b948cac07264aef4527dd14b2aa28d10c6f8d61c7682011`. Independently re-parsed all 360 JSON outputs against frozen source export, recomputed each action, oracle, per-arm counts, detail SHA, source identity and receipt; exact score match.
- Mean per-call duration **0.237s**, max **0.601s** on Linux x86_64; **not Redmi** measurements.

| Arm | Exact | Wrong committed | UNKNOWN | Unparseable |
|---|---:|---:|---:|---:|
| c3_only | 0 | 72 | 0 | 0 |
| b1_only | 0 | 72 | 0 | 0 |
| b2_only | 0 | 72 | 0 | 0 |
| both_exact | 24 | 48 | 0 | 0 |
| shuffled | 0 | 72 | 0 | 0 |

Action distribution: **NONE** for all 72 outputs in each of c3_only, b1_only, b2_only and both_exact; shuffled **70 NONE, 2 B**. The `both_exact` 24/72 equals the number of frozen held-out oracles whose answer is NONE, so the baseline provides **no demonstrated discrimination between A, B and NONE** and commits incorrectly on every negative source arm. This is **FAILURE of source-sensitive utility**, despite successful native execution. Do not reinterpret the 24/72 as learned reasoning, or claim any improvement over chance without a preregistered comparator.

## Limits / next steps
This is **one frozen prompt view and constrained output grammar** on Linux. It does not isolate whether the failure arises from task understanding, prompt format, output grammar, model capacity, lack of B1/B2 integration or training. The original native LoRA one-step pilot has not been evaluated against this baseline; **no AG6 approval or live adapter activation**. Any new prompt/system-message ablation must be prospectively registered as a distinct cohort/view, not overwrite P2X validation input SHA or tune on this held-out oracle. Do not reuse P0X holdout for tuning.

Next: preserve this negative baseline and independently review prospective C3 format/source sensitivity and JEF/Context OS pathways. If candidate adapter loading becomes explicitly approved, preregister exact adapter GGUF SHA and run paired disjoint validation under the same frozen inputs; do not merge or promote based on this baseline alone. Actual Redmi TESTEN.sh remains device-blocked.

**All binding negative gates unchanged:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; Redmi unmeasured; V13 INCOMPLETE.
