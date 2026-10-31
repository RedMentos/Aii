# BUILD_STATE — Run104 optional phone C3→JEF/C5/C6 + STEP2_EXIT smoke GREEN, 2026-10-31

Owner GPT-6 automation11. Review-only child of PR #1474 exact parent `70dc2e169465e948c24514ca5aebe33a4ca8fea0`; no parent/other-owner overwrite. Initial prereg `586865fb597313c306a7deae7ca07b7cb3d3b884`; follow-up timeout Boolean prereg `91283634ebdfbf30663fb82af50c2514d52ba52b`, both before remote implementation.

## Implemented

New **optional** 21-case `run104_c3_c5_exit` bounded model-free first-install cohort in `scripts/install_selftest.py`, preserving exact `legacy_run97` 18 and `run102_c3` 18 cases, original names/order/digests and default. Added three actual Store-backed cases: six JEF/C3→C5/C6 SHADOW DRAFT and restart checks; strict missing-native binding refusal without memory changes; original STEP2_EXIT native-negative gate with dependent gates not GREEN. The installed `setup.sh` **still selects `run102_c3`**; Run104 is opt-in only via `scripts/install_selftest.py --cohort run104_c3_c5_exit`. New cohort SHA256 `d745f4a1df7d54f7b1c1024e7d3aa24603d007070a694a6611d50ba958b96d70`; original digests `31b7d96e...`, `218303e4...` unchanged.

Local adversarial test initially **RED** (4 tests, 1 failure) because `run_bounded(True,...)` accepted Boolean as integer and launched a one-second worker that timed out. Preserved failure in follow-up prereg; narrow guard now uses `type(seconds) is int`, rejecting Boolean before launch without altering valid 1..120 integer semantics. Local corrected 4/4 contract + 21/21 bounded worker PASS.

## Closed Linux Actions software evidence

Actions **41209326777** terminal SUCCESS at exact tested HEAD `72006c6bd4f809895fbb2974817d4c5f94f869d5`. All **14/14** reported stage exits zero: original installer contract 5/5, Run102 cohort contract 5/5 (nested worker 18/18), new Run104 contract 4/4 (nested worker 21/21), JEF/C5/C6 CLI 6/6, STEP2_EXIT 7/7, C3 Context OS 3/3; extracted ZIP Run104 contract 4/4 (nested worker 21/21), extracted direct Run104 21/21 and original Run102 18/18. `STEP2_EXIT=EVIDENCE_NOT_PASSING` in extracted ZIP, original Z2b/Z2c `canonical_gate_pass=false`. Privacy CLEAN, compile/diff PASS, no model downloaded/executed, no Redmi.

Original phone ZIP `V13-Phone-Run104.zip` 15,432,074 bytes SHA256 `ef1f0d25404423ecc285ffd1f44bebfbfc4bd6f04db4b14cd29565846e89933a`, ZIP CRC PASS, **2,100/2,100** manifest hashes match original and extracted bytes. Original Actions artifact `13045756889` 15,123,524 bytes SHA256 `57cce9c360b6180a8ddb77156c97930e9250b0658eb67f229dfac2a8f7cda69b`, CRC PASS, **41/41** inner SHA256SUMS PASS. Original downloaded and independently hashed. Private persistent Library backup (not rejected Drive): `/V13-Checkpoints/2026-10-31/Run104-Phone-C3-C5-Exit/ORIGINAL_GREEN_ACTIONS_41209326777_SHA57cce9c3.zip`; independent private Library re-materialization hash matches.

## Current gates and next step

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight=0; Redmi UNMEASURED; canonical/full V13 INCOMPLETE. No native weights, no visible output approval, no tools or learning authority. PR remains review-only, not production-integrated.

Next independent package: preregister and run **unfiltered full software suite** on this exact Run104 review chain with pinned dependency environment and two original native ZIP prerequisites, using Run94 original-raw workflow as historical control; capture terminal raw, errors/skips, privacy, hashes and private backup. The local extracted-source full-suite attempt was stopped at 180 seconds before completion and cannot be called a pass; Run94 earlier 4907/28 skip GREEN applies only to its exact older HEAD. Current source has additional tests and must be remeasured. Heavy native owners remain untouched. Next command for full-suite runner: `cd v13/code && PYTHONPATH=.:tests:scripts python3 -m unittest discover -s tests -p 'test_*.py'` after staging original pinned ZIP prerequisites and isolated dependencies. Platform remaining budget UNKNOWN.
