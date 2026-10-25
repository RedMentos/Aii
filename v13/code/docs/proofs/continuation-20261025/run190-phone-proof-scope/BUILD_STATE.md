# Run190 BUILD_STATE — 2026-10-25 (Phone source ZIP historical candidate scope)

## Provenance / ownership
- Parent: Run188 PR217 head `f9d829fac1b3c6190c7f4745d26ef6361d26d711`, not older Run24/PR60. Run189 B2/C3 heldout owner is separate and untouched.
- Work branch: `codex/run190-phone-historical-proof-scope-20261025`, PR218 (draft).
- File ownership: ONLY `v13/code/tests/test_package_source.py` plus this new Run190 proof. Frozen `v13/code/v13/**`, source snapshots, native firing candidate, model/seed/runner pins and all Age/learning gates unchanged.
- Old source-bound candidate tests must not be mistaken for current Phone runtime tests. The current Runtime is later than the native-firing frozen baseline; exact `native_firing_runtime_candidate.sources()` refuses `Live sources differ from complete baseline/candidate` correctly.

## Reproduced RED evidence (unchanged historical job)
- Run188 generic focused workflow `40170719093`, job `121100811944`: **FAIL**, step `Execute extracted V13 Phone source smoke without models`.
- 401 software regressions earlier in the same job passed; extracted phone smoke 100 tests, 2 outer failures; their nested 17 historical candidate tests refused source drift with `ValueError: Live sources differ from complete baseline/candidate`. This is not a native model failure.
- GitHub decoded job log (UTF-8) SHA-256 `7580f826613ade52e1f649e93ed451689c24658c4fa2d0c8cd9ba7bdab6a37f3` (189239 JS string characters). Original log remains at `https://github.com/RedMentos/Aii/actions/runs/40170719093/job/121100811944`.
- Historical failures retained; no rewriting original tests or original proof.

## Implemented and independent CI
- Exact frozen candidate source: run original historical candidate suites, unchanged.
- Later live source: demand exact expected fail-closed refusal for both direct loader and merged firing path; unrelated missing/corrupt snapshot errors are **not** accepted as stale.
- Independently fixture-bound approval-reader suite still runs on the extracted ZIP.
- New corruption-negative-control test tampers with archived `runners.py` in a throwaway extracted ZIP and asserts the stale-classifier refuses to classify it as ordinary revision drift.
- Git blob `v13/code/tests/test_package_source.py` = `2989a5867c25558998c7328850e276a0d9d26a21` (remote bytes independently reread). First code commit `45822d71b54c11cf2ec308193efb0b91a2ec7019`.
- GitHub focused CI `40171176726`, job `121102126591`: **SUCCESS**. 401/401 source-bound SQLite/software regressions, official added-lines privacy scan **CLEAN**, source ZIP manifest 934 entries, independent ZIP audit PASS (SHA-256 `408cbee230d9a4ca66a85b5f721b0492aae61d190bca05af2b432f2f001f702c`), extracted phone smoke **101/101 PASS**, runtime restart PASS. No native model invoked.
- GitHub decoded successful job log SHA-256 `47e45c0862542746114e56b3c5034c7d47ce3da415228fd808ba7450b00f1490` (130073 JS string characters). Immutable job `https://github.com/RedMentos/Aii/actions/runs/40171176726/job/121102126591`.
- Test scope is **software/Linux CI**, NOT real Redmi, full repository suite, historical candidate behavior on its exact historical runtime, native JEPA or LP3 cgroup proof. No production integration change.

## Gates / blockers / next
- STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; DS2 H2 `FAIL`; full V13 `INCOMPLETE`. Generic CI success cannot promote them.
- Native Redmi long-run, real cgroup delegation, full suite orphan-descendant failure and learning utility remain open. Active Run189 native Gist owner must not be overlapped.
- Exact next independent package: inspect `v13/code/specs/gate-graph.json` STEP2 verdict (row integrity != complementary utility), bind to existing negative native evidence and add a non-promoting gate regression without editing Runtime or Run189. Then pursue end-to-end utility and mobile proof when prerequisites/owner allow.
- Exact reproduction: `python3 -m unittest -v tests.test_package_source` from `v13/code` in full checkout; `python3 scripts/public_repo_privacy_scan.py --base f9d829fac1b3c6190c7f4745d26ef6361d26d711 --head HEAD`.
- Rejected anyone-writable Drive backup destination not used. GitHub remote is the verified source checkpoint; no new private material published.
