# Run285 — source-only Termux diagnostic does not provision (2026-10-25)

## Source and independent ownership
- Base: PR284 `d3d0c00819d847877d85fc35e5fad3556187f7cc`; current source-under-test: `04d6f0a04eca5eee031da488f9b8abd5f6638d11`; PR285 is draft, branch-scoped and **not** merged into main.
- Owner: `v13/code/setup.sh`, `tests/test_offline_diagnostic_no_provision_run285.py`, Run277 isolated-interpreter fixture only, Run285 CI and this proof. Runtime/Canon/model registry/seed/learning paths untouched. Run284 Runtime owner remains separate.
- Canon original SHA256 `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee` verified by exact-head CI.

## Actual defect and changes
- Prior exact-head Run277 `40189028071` **FAIL**: source ZIP integrity PASS but offline setup attempted `python3 -m pip install numpy` with PIP_NO_INDEX; `PREFIX=*com.termux*` would also call `pkg update/install` before reaching source-only branch.
- Run285 makes explicit `V13_SOURCE_ONLY_DIAGNOSTIC=1` bypass both Termux package manager and pip. Preinstalled Python >=3.10 and NumPy are mandatory; if absent, report refusal and never install. Source hash verification still precedes imports/state; diagnostic runs actual Age-0 `doctor`, not native inference.
- Normal setup still uses Termux pkg, pinned bootstrap, selftest and native probe. Prior Run277 test subprocess now binds to the CI's already-provisioned isolated interpreter instead of system Python, with no test or gate relaxed.
- New adversarial tests run an **actually extracted source ZIP** with simulated Termux PREFIX, failing `pkg` and `python3 -m pip` sentinels, no-NumPy refusal, tampered-source refusal and normal-mode preservation.

## Closed actual evidence
- First Run285 head `f87c2b20fa132790621587a2c1320476558c0b87`: CI **FAIL**, Python test literal SyntaxError and prior missing-NumPy fixture; retained at Actions run `40193605342`.
- Intermediate head `8247df5f1f59620c6f6826ad7a50fe5d62406eff`: Run285 adversarial 4/4 PASS but prior Run277 isolated Python fixture FAIL; Actions run `40193712805`. Preserved, not relabeled as green.
- Exact tested source `04d6f0a04eca5eee031da488f9b8abd5f6638d11`:
  - Run285 `40193718675` **8/8 PASS**, compileall 0, official privacy CLEAN. Raw artifact `12598209121`, independently downloaded ZIP SHA256 `1ba5bdab2f87d4e3851586e0d63c745c2b796cf5b20a114905eab9a06c5ab4b8`.
  - Run277 `40193718701` **4/4 PASS**, package and independent manifest/CRC/parity verification PASS, privacy CLEAN. Phone ZIP SHA256 `5404406db219ea7147c4875dac6577711eab52a87fb8691c8f59bf46ff526a61`, 997 registered source files. Raw/ZIP artifact `12599261458`.
  - Focused source-bound `40193718792` **401/401 PASS**, extracted phone runtime/restart **114/114 PASS**, privacy CLEAN; independent ZIP 997-member parity PASS, artifact `12598957161`.
  - Independent Linux-local extraction of exact Run277 artifact: `8/8 PASS`, Git blob checks setup `4b4a24a3ad4a01699d65f4bbae29fd79c8d19cbb`, new test `21dc73e2ea27c487bdac388b0d4ecef15502211b`, prior fixture `750d90253b0514d2e07afe5bcfbdff6fe5a1390e`. An extra broader local test run exceeded the local 120-second command limit after 25 individually passing cases; it is **INCOMPLETE**, not a full-suite PASS.
- Raw artifacts: https://github.com/RedMentos/Aii/actions/runs/40193718675/artifacts/12598209121 and https://github.com/RedMentos/Aii/actions/runs/40193718701/artifacts/12599261458. Action artifacts have finite retention; source/proof/checksums remain in Git.

## Claims and next step
- Scope: **Linux-software / extracted ZIP / simulated Termux** only. No actual Redmi, no native model, no actual mobile package-manager proof, no Body-JEPA, no real learned utility.
- Original gates unchanged: `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `jepa_weight=0`, `V13=INCOMPLETE`. PR269 full native 12/20 PASS and 8 FAIL remains; PR284 cancellation RED remains.
- Exact next: independently review Run285 shell default-mode parity and run the diagnostic on real Termux when operator permits; then return to unresolved registered native utility gates (readout Halt Pareto, control calibration support, output adapter calibration/accuracy, memory B1 source use) and PR284 cancellation without changing original thresholds. Never merge isolated PR285 into old main.
