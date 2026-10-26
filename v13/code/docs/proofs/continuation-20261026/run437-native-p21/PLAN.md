# Run437 — separate P_s21 native attempt after RED-first CLI repair

Date 2026-10-26. Owner GPT. Branch `codex/run437-native-p21-cli-fixed-20261026` based on corrected Run434 source checkpoint `7916b29f7f3904689fd2d484f397bd3db1b00a27`. **This is not a retry of closed PR434/Run435.** Both Run435 Actions 40265963506 and 40266123125 failed at argparse before native inference, original small raw artifacts 12625924197 and 12625929445 preserved. The second was accidentally triggered by a docs-only commit on a PR whose workflow file remained in the PR diff; never commit to this native branch after opening its PR.

Run434 RED-first CLI source test Actions 40266144461: 51 total, 1 expected failure. Fixed exactly one flag `--stage3-report` -> `--stage4-report`; GREEN Actions 40266234440 51/51 PASS privacy CLEAN, corrected source SHA256 `84f169825f887a678e5441c4c22e272c5d3768832967ea1da9fbe20fd1bfbb6d`.

Use same verified Run427 168-row producer and Run433 independent postflight; raw ID 12626041558 SHA256 3f7b66330778bd2129673c74d2917dcfe9b6ef8e2281df7f8557fd5c89bcecf5, safe ID 12626146409 SHA256 405e62268b0314c6e852e367a4624a12508e971877afe14afebf05cb2afba6b7. Exact one P_s21 via Run434/unchanged Run397; expected 210/378 structural rows. Serialized `v13-native-c3-run131-serialized`, no cancel, no auto retry, safe archive on RED or GREEN, raw receipts and source pins closed, no model weights published. Source test and CLI --help gate must pass before model provisioning.

Once native PR triggers, **do not push anything else to this branch**. Record subsequent status by PR body, a separate review branch, or Library; otherwise GitHub may launch another native workflow. On failure, preserve and stop this attempt. On GREEN, independent Run436 verifier on actual artifacts before S_s21.

All negative gates remain: STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi unmeasured, whole V13 incomplete.
