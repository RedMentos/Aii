# HX134 request revocation + evidence freshness — verified software result (2026-10-27)

Review-only PR #789, child of PR #788; **reintegrates previously tested PR #163 / Run133** from an older branch into current HX134. Parent source `72b48d1b89bb73c8ffd6d7434a0e75242db349c3`; prereg `a88e8eff7bcb5f92c10b324c7f540f8a07f65654` before exact prior test blob `243caf41dafe914697867b4ee2bd3ab5f5db8a8d` and RED workflow. No overwrite of PR #163.

**RED Actions `40596029345`** at `7d80224d51bd548e1909e41f8f35763f14b15c16`: 27 tests, **2 expected failures** (revoked human request still accepted by both HX writers; changed evidence still returned by lookup). Original artifact `12776056665`, SHA256 `64ebf08b384e36c3e22e973f31a19825ed2af043e1d9b61e39614c259655f375`, CRC/internal hashes PASS.

Fix `6634498f24bbd3ae5528e3225bf9bf484f0454f5`: AG8 helper now queries the **current** persisted request row and rejects missing/revoked approval; HX3 lookup refreshes changed/unreadable evidence to STALE before returning any lesson. **GREEN Actions `40596135925`**: 27/27 PASS, raw exits0, privacy CLEAN; artifact `12776510904`, SHA256 `46bfdb6ccd3bd56b5ad71cb367010a53a33ff864c884bb87feab6214c049ac04`, CRC/internal hashes PASS.

**Full Actions `40596239077` SUCCESS** at exact tested HEAD `7a56a53018fa6db9c0d783ee45065ee4dfaf4bed`: 27/27 focused, **2024 full software tests OK (1 skipped)** in 223.263s; `PREREG/RED_TEST/FROZEN/INSTALL/FOCUSED/FULL/COMPILE/PRIVACY/DIFF` raw exits all 0, privacy CLEAN. Original artifact `12776461924`, SHA256 `92b3a12717c05f27baf215a963e9c1a6d69697e1234a80c2c0b57ac617627b7c`, CRC/internal SHA256 PASS. All RED/GREEN/full original ZIPs privately saved and re-materialized byte-identical at `/V13-Checkpoints/2026-10-27/Automation11-HX134-Request-Evidence-Run133/`.

Frozen source blobs: `self_improve.py=0f71e36b9542f1aa3aa57db734c448c305dfb48b`, `harness.py=78e3fd6c6c40a75db9cb88ea683194011e058d6f`, `experience.py=83ede4b83161bc78b5cc718c647d984e06d9f54a`, `test_hx_approval_run133.py=243caf41dafe914697867b4ee2bd3ab5f5db8a8d`.

**Claim limit:** Linux software, no native receiver, Redmi, live harness consumer or measured utility gain. Age0, authority0, B3 L1 FAIL, STEP2 UTILITY_FAIL, LP1/LP2/BJ1 negative, `jepa_weight=0` and whole V13 incomplete unchanged. Downstream PR #790 integrates separately verified PR #375 / Run380 strict AG8 metric shield; cross-organ C1+World+B3+Sleep integration remains review-only and must run full suite again. No production merge/auto-merge.

Owner GPT integration reviewer. Exact next command: `cd v13/code && PYTHONPATH=.:tests python -m unittest discover -s tests -p 'test_*.py' -q` on next combined candidate, plus privacy and source hash checks.
