# Run128 independent review — superseding frozen-runtime-safe Widget preflight

2026-10-25 UTC. Exact base Run123 PR #154 d3aa8dde0f521ecd3f4920820743a3d3bbad12bc. Run126 PR #157 independently exposed a correct SourceHandoff rejection of Run124's frozen Runtime mutation (2238 tests, 8 FAIL / 63 ERROR / 11 skips). This candidate DOES NOT import Run124/125 Runtime changes. Run127 PR #158 owns installer quoting separately and was not touched.

## Source identities and scope
- `v13/code/v13/runtime.py`: Git blob `a691d27bd0772a4fa1f03d57ec90663237bf6825` — byte-identical to frozen baseline, independently read back.
- `phone_halt.py`: `93e91553ebd591a2306c48ae6e1bcb4505eaeb5f`; `__main__.py`: `b869611118f1e292fdffe9a11189a650adad3592`.
- New test: `9eaf100383bf24f3d26246393464e55a2b9a3536`.
- No other Runtime, UI, operator, installer, model, Canon, registered cohorts, or other owners modified.

## RED / GREEN
- Preregistered tests-only RED Actions 40153412873, software job 121049578636: 6 tests, **1 FAIL + 5 ERROR**; CLI recovered queued turn reached FINAL before Widget stop. Full `RAW_RED_JOB.log` committed before implementation.
- First GREEN Actions 40153517026, software 121049909535: 28/28 focused Linux software/SQLite tests PASS (6 new + 6 Widget + 2 CLI + 14 Stillstand). Full raw log committed.
- Adversarial crash-window replay and corrupt-state CLI refusal added. Final GREEN Actions 40153666770, software 121050351354: **30/30 PASS** (8 new + 6 Widget + 2 CLI + 14 Stillstand), compileall PASS, official privacy CLEAN. `RAW_GREEN_FINAL_JOB.log` committed.
- Existing source-bound focused Actions 40153517041 on same source blobs (before tests-only addition): 401 + 100 = **501 tests PASS**, official privacy CLEAN. Raw log `RAW_SOURCE_BOUND_JOB.log` committed. Later runs can be cancelled by evidence-only commits; no inference from a cancelled run.
- Inherited Run121/Run123 workflows on same source blobs PASS (40153517032, 40153517022).
- Independent local Linux reconstructed candidate: exact three source blobs (Runtime, phone_halt, __main__) match remote Git blobs; 13 assertions PASS including queued turn, ownership, corruption rollback, crash-window retry. Local reconstruction used Run125 source-only archive with Runtime restored to frozen bytes, so it is NOT an exact complete Run128 checkout and is not presented as full-suite proof.

## Behavior / failure modes
- `python -m v13` CLI preflight applies preexisting STOP file using Store's exclusive coordinator lock and ONE SQLite transaction before Runtime constructor creates worker.
- STOP gates: durable queue pause, Notaus, Age freeze and original ownership record; request files acknowledged only after COMMIT. Retry after commit-before-rename preserves original release ownership.
- Corrupt Age/Notaus/Stillstand state fails closed before Runtime starts, leaving request pending. `NOTAUS` alone does not freeze Age or pause queue.
- Direct `Runtime(home)` users do NOT invoke CLI preflight; this is a documented scope limit. A button pressed after CLI preflight but before UI watcher starts has a remaining race; do not claim universal preworker safety.
- No native model, Linux cgroup, Redmi, hardware timing, generated-answer utility, or whole-system acceptance measured.

## Gates and next step
STEP2=UTILITY_FAIL, B3 L1=FAIL, Body-JEPA=UNAVAILABLE, jepa_weight=0, DS2 H2=FAIL, V13=INCOMPLETE. No gate promotion.

**Next:** Run129 bounded full-suite audit on exact Run128 final head with pinned torch 2.9.1+cpu and sealed Run16 LP3 helper temp-only; preserve raw failures and compare Run126 (8 FAIL/63 ERROR) vs Run115 (4 FAIL/1 ERROR). Do not weaken source-bound validators. Then select independent substantive canonical package; do not loop only on LP3 helper. No merge into production yet.
