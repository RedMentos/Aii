# Independent raw audit: corrected Aquila TP/s27 native pilot (2026-10-28)

Owner: independent automation review branch, based on #915 at `e1066968369be7e5178f3edb745c5df1e2e0a491`. Scope: **Linux-native, one frozen Aquila fixture, seven variants only**. This is not STEP2 criterion 3 or Redmi evidence.

## Frozen source and original evidence

- Corrected #914 Actions run **40683211643** completed SUCCESS at exact source `44eb8e85aa6ac2cc6292cced515f97cad27af9d9`; artifact **12814207610**.
- Downloaded original GitHub Actions ZIP and independently inspected its bytes (not merely the workflow conclusion). ZIP SHA256 `ff05974753c3151e92ed14194c0f254ce6ea721b610fa16e6490a064bd343ea7`, ZIP CRC clean, **26/26** inner SHA256SUMS match, HEAD.txt equals workflow source SHA.
- **11/11** stage exits zero (BLOBS, INSTALL, FOCUSED, COMPILE, BOOTSTRAP, NATIVE, REPLAY, FULL_INSTALL, FULL, PRIVACY, DIFF); **29/29** focused and **2351** full software tests PASS (**1 skipped**), privacy CLEAN, diff clean.
- Original `STEP2_RAW.json` SHA256 `786ea4d7ff90fc6709219c4298b8d3926cac62bc3fe698d92355d2bdb0fb853a`, equal to receipt; independent canonical JSON row recomputation **7/7** matches report row_sha256. All seven are **Aquila** (not Kestrel), RECORDED, C3 native FINAL, processes reaped, restart identical, oracle invisible to native. All **12/12** body offers had the fixed JEF question.
- Registered fixture SHA256 `b721650791284e4369d440d494de4aaf76da35fe4be11e34cb87bba1285e4040`; B1/B2 model hashes distinct and unchanged before/after. B1 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, B2 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`, C3 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`.
- Independent private Library backup at `/V13-Checkpoints/2026-10-28/Run11-STEP2-TP27-Aquila-Pilot/RAW_40683211643_shaFF059747.zip`, **re-materialized and compared byte-for-byte**, SHA256 unchanged. Raw report and private model responses are NOT added to public Git.
- The earlier wrong-cohort Kestrel Actions **40682422549** remains **RED**, separate, unaltered and in its original private backup.

## Utility (descriptive, not an acceptance gate)

Aquila single-fixture source-native scores: b1_only 0.6667, b2_only 0.0833, both_none 0.6667, both_exact 0.6667, both_control 0.6667, same_policy_dual 0.5833, prompt_only_dual 0.6667. The **paired report is incomplete** (one of ten episodes); no demonstrated two-body gain, no complementary profile conclusion, no CI, and no STEP2 gate promotion. Receipt: `PASS_SCOPED_ONE_FIXTURE_NATIVE_NO_UTILITY_GATE`, report: `DIAGNOSTIC_INCOMPLETE`.

## Decision and next authorized package

**Pilot prerequisite for #915 is satisfied at the narrowly scoped raw-evidence level.** Implement full frozen TP/s27 ten-fixture × seven-variant **70-row** Linux-native collection followed by **70-row** C3 typed-value tool replay; source-pin new wrapper and workflow, fail closed on missing/duplicate rows or model drift, retain every error. Do not change original fixture/seed/model/runner source, do not silently substitute Kestrel, and do not promote any gate from a one-arm run. Required original four-arm × three-seed criterion remains separate.

Gates: STEP2 **UTILITY_FAIL**, B3 L1 **FAIL**, Body-JEPA **UNAVAILABLE**, LP3 **FAIL**, `jepa_weight=0`, Age0 **RECORD_ONLY**, Redmi **unmeasured**, whole-system **incomplete**. Production main unchanged. Remaining platform budget: UNKNOWN.
