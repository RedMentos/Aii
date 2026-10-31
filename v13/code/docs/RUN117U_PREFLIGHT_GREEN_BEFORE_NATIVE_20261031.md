# Run117U model-free preflight GREEN — checkpoint BEFORE native launch

Owner: isolated review branch `assistant/v13-run117u-seed1061-native-threearm-20261031-1923`; parent `2448c8d06085c4ac728c6bc1f677ff474a85c089` (#1500 on #1499). Preregistration first `815634d49b29fd57cd703bafea894474291034ae`. Frozen seed1061 fixture SHA256 `11d499eeb04d83e3786fe12046207ec3d0fc6684f5220a5fc1943202cd0f31de`, Git blob `f7741de466571e67e48720395f32acbcb32ff14a`; no fixture/model/runner edits.

New native runner `scripts/run117u_seed1061_native_three_arm.py` Git blob `1b06bb8b6f237f21f9d1df7e8a15bb2e0a74ff8e`, tests `tests/test_run117u_seed1061_native_three_arm.py` blob `8000b79e683c135bb5633ee38a8d0442676d4907`. Controls RAW_FULL_SOURCES and SOURCE_SPANS_ONLY run even if Body quote arm unavailable; all three C3 prompts use source data only in USER role, no oracle/JEF answer injection. Native path uses pinned Run113B models/runner, sequential process reaps, strict offline scorer and durable real Store. All live authority remains 0.

Original GitHub Actions **41229227104 terminal SUCCESS** at exact `b37cbdcf62d394fe2938229d49a17929398b9866`: **24/24 tests PASS**, frozen fixture SHA PASS, 6/6 real SQLite synthetic QuoteBody preflight PASS, compile PASS, privacy CLEAN, diff 0. Original artifact ID **13053380095**, ZIP SHA256 `ffd1298e8fd5808498e1bfcd5c2aeb234bb4821f95a111fa46bf67edcbe4e91d`, CRC PASS, **21/21** SHA256SUMS checked. Private byte copy at `/V13-Checkpoints/2026-10-31/Run117U-Native-Seed1061/run117u-preflight-green-b37cbdcf.zip`. This is **not native model inference**.

Next exact step: create the hash-pinned native Actions workflow on this branch, using `package_source.py --phone-install`, verifying source manifest and frozen fixture, `run93_source_c3_native_e2e.py --home INSTALLED --install` then ModelManager install body/gist and deep-verify, and invoke:
```sh
cd V13-Phone
PYTHONPATH=.:scripts:tests python scripts/run117u_seed1061_native_three_arm.py --fixture ABSOLUTE_FROZEN_SEED1061_JSON --installed ABSOLUTE_INSTALLED_HOME --work FRESH_WORK --out FRESH_EVIDENCE_DIR
```
Keep native concurrency group `v13-native-c3-ag12-20261030`; original raw ZIP, exits, hashes and process-reap receipts even on RED. No native launch claim until Actions run appears. Do not overwrite Run117T owner branch or change frozen cohorts. All STEP2/B3/Body-JEPA/age/Redmi/whole-system negative gates stay unchanged; `jepa_weight=0`. Native evidence not yet obtained. Runtime budget UNKNOWN.
