# Run359 — STOP widget re-engagement after interrupted standstill release

Base: Run357/PR353 `9c74c2d8ed74c5002259da10c4a6b541382dfa14`. Review: PR354. Owner: `assistant/run359-phone-prestart-release-20261025`; changed `v13/code/v13/phone_halt.py`, a new isolated test and workflow only. Run358's native-firing workflow and the frozen Runtime remain untouched.

## Observed RED before patch

Exact-head Actions run [40229099289](https://github.com/RedMentos/Aii/actions/runs/40229099289) on `cc209b4b22fb12ce407c5a06a259fce076122251`: **15 tests, 2 failures**. One real crash-window failure: after a human `:stillstand aus` was interrupted before `resume`, the durable `release_pending.queue=True` was lost when a STOP widget re-engaged at startup. The later explicit human release therefore incorrectly left the queue paused. Another test showed malformed pending ownership was silently accepted. Original 13 related regressions passed. Raw ZIP artifact 12611902922, SHA256 `b8dcc876a24d5e439d19e0b0d0b818a53de1d97b24487a85c0125ffea7664381`. Workflow itself also initially inherited Bash `-e` and skipped privacy on RED; this was corrected without deleting the failed test log.

## GREEN and code change

`phone_halt.prestart` now validates the persisted `release_pending` shape, carries its original ownership into the new STOP engagement, and clears the obsolete pending marker atomically with the new `on=True` state. The original user's pre-existing Notaus remains held. Exact-head Actions [40229181464](https://github.com/RedMentos/Aii/actions/runs/40229181464) on `37116e789f892ee3dbcc09ab7526ece438a908bd`: **15/15 PASS, 0 failures/errors; privacy scan CLEAN**. Raw ZIP artifact 12612755964, SHA256 `5904654636443eee20a92b795d33d8ce3e7b2207f7822d77718e0b910aeee7ce`. Source and workflow blob SHAs, central BUILD_STATE snapshot SHA, owner, next command and unchanged gates are in `BUILD_STATE_RUN359.json`.

This is **Linux software/SQLite only**, not Redmi, native model learning, STEP2, B3, Body-JEPA or whole-system proof. No learning, Age, approval or source/model hashes were promoted or changed. The current source suite's pre-existing historical/frozen applicability failures are not concealed.

## Next work

Review PR354 against its Run357 parent, integrate only after conflict/source-lineage review, and continue the independent highest-priority functional blueprint package. Local rerun: `cd v13/code && python -m unittest -v tests.test_phone_prestart_release_recovery_run359 tests.test_phone_prestart_run128 tests.test_standstill_release_recovery_run348` with `numpy==2.3.5` and `prompt-toolkit==3.0.52`. Redmi verification remains a separate prerequisite.
