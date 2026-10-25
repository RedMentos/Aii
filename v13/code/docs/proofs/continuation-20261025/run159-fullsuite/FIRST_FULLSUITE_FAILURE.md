# Run159 first full suite failure, retained

GitHub Actions run 40162711504, job 121077485472, exact head `ce7dd524d52f41e4e50f6d11bb61141ba20cc1d9`, 2026-10-25. Privacy job PASS/CLEAN. CPU full suite ran **2344 tests in 154.174s: 4 failures, 3 errors, 12 skipped**. Raw closed log artifact ID 12586299250 (30-day retention), ZIP SHA-256 `1d344e62deb60b4832181b233ecb15dc48d4905b0dac23ff89ad52c7f1bb7675`. The workflow correctly failed; no gate promoted.

Errors: (1) Run148 audit missing registered Run147 ZIP at hardcoded /mnt/data/RUN147_native.zip (can use RUN147_ARTIFACT env and exact pinned ZIP); (2) Run18 LP3 lock-poison test expected `_cleanup_owned_group`, absent from older Run16 helper; (3) optional `/root/native/restore/round8-note-tool-raw` check raised PermissionError under nonroot CI.

Failures: three duplicated inherited LP3 Run16 default CLI tests expected exit 2 but got 1; one Run18 orphan descendant safety check observed forbidden `LOCAL_CLOSED_EVIDENCE_UNPUBLISHED_ANCHOR`. **Do not suppress the orphan failure or call the suite PASS.** Stage exact Run21 helper, then independently reassess. The older Run16 helper is not the current LP3 candidate.

Workflow: https://github.com/RedMentos/Aii/actions/runs/40162711504
