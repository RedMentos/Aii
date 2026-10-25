# RED actual-source evidence — 2026-10-25

- Exact branch commit: `f18fa42e71b80c902a18ac329934c6901f080d2a`.
- GitHub Actions run: https://github.com/RedMentos/Aii/actions/runs/40183615317
- Job: `121139657712`.
- Actual-source adversarial tests: **6 test methods, 7 assertion failures** (tampered packet has 3 subcases). Valid-source control passed; revoked/missing/cross-source/tampered/unreadable source accepted incorrectly by unmodified production WorldModel.
- Raw log artifact: `12595385956`, uploaded ZIP SHA256 `86127dd645c4d9750d2360dfb86627d98157a4f89d6813c21f9ea6a7d83d5c6a`. Logs preserved; not a passing result.
- Test source blob SHA before fix: retrieve from commit `913b095db21100e63f0cf308c4dffbf51421976d`.
- Scope: Linux GitHub Actions + synthetic SQLite, no native model, no Redmi, no full suite.
- Next: narrow production source verification, repeat adversarial and compatibility tests; verify exact new head and privacy scanner.
