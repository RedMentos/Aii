# Run625 prereg — exact-current source-only Termux ZIP, extracted Sleep A integration

2026-10-27 UTC. Parent: Run624 PR619 branch `codex/automation11-run624-sleep-session-fairness-20261027`, exact head `7422985fa3fd97e74b58ad635c28f49faf5dadb3`, itself a child of Run623 PR618. This package owns only its new GitHub Actions workflow and `run625-phone-source-sleep-fairness` proof files. No source changes, model revisions, frozen cohorts, private data, Canon edits or authority promotions.

**Objective:** deliver a complete, runnable *source-only* `V13-Phone` ZIP including the new Run624 Sleep A fair multi-session scheduler and Run623 idle-atomic operator changes. Use existing pinned `scripts/package_source.py` and independent `scripts/verify_phone_zip_current_run268.py` without modifying them.

Precommitted gates:
1. Bind exact parent source blobs: `sleep_offline.py` `0525bffc887efd91a26a67f94a38f7eab2cdfd0f`, Run624 test `bea79648409efc7d6f23fa02a110a74fa09ea5a7`, Run623 operator `9b928d1cce3dfc1466b564cf20130cb9e7af8706`, packager `06167e0bcb82b36cb08841cd31b9618c4ba0926e`, verifier `880dbd2cebb0aac5c7b37e25a5ca8487b796cfa1`; frozen Canon SHA256 `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`.
2. Build `V13-Phone-Run625.zip` with `--phone-install` from the **exact checked-out head**. Independent verifier checks every ZIP member SHA against the checkout, CRC, manifest, executable launchers and absence of model/private payloads.
3. Extract to a separate path and run real SQLite Runtime tests on the **extracted** source: Run624 four new multi-session cases, selected Run609/610/612 Sleep A source/history regressions, Run623 operator config, language/prompt and B2 gist read-only cases. Preserve full raw/exit logs; source-only dependencies pinned and isolated.
4. Privacy scan only the exact new branch delta, SHA-close original logs and ZIP, upload artifact with >=30-day retention, independently verify downloaded artifact and save to private Library.
5. Negative gates remain `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `V13=INCOMPLETE`. **No model weights**, native inference, Redmi installation, training or AGI completion is claimed.

This is an operator-usable source deliverable, not full-system acceptance. Historical failed attempts remain preserved.
