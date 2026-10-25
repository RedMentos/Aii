# Run266 first ephemeral patch preflight failure (2026-10-25)

- GitHub Actions run https://github.com/RedMentos/Aii/actions/runs/40186212183, job `121147430029`: **FAIL**, exit 1 before isolated Python deps and before focused tests; no candidate result and no native execution.
- The original preflight combined a Git blob equality assertion with `git apply --check` under `set -e` but did not log intermediate values. The job log shows exit 1 without patch stderr; exact failing assertion was not independently identified. The full GitHub job log is preserved; no raw artifact was created.
- GitHub connector independently read PR266 and PR261 `world_model.py` blob `db62c761a9b1f3364c951ad6ac82a71f3a71d84f` byte-identically. A locally reconstructed patch context passed `git apply --check`, but that is not a GitHub checkout proof.
- Fix commit `4667c03b839a114fb53cbecb540d4568794c073b`: explicit exact PR head checkout, record `EXACT_HEAD` and actual `WORLD_BLOB` in `RUN266_PRECHECK.log`, run verbose `git apply --check`, preserve precheck in raw artifact. Do not alter owner production source or relax SHA assertion.
- Next: inspect corrected CI. If source or patch differs, stop and report exact bytes instead of patching blindly. All original negative gates unchanged.

## Root cause identified after raw artifact retrieval

Corrected preflight run `40186330142` (job `121147789126`) still failed before patch execution. Closed raw artifact `12596113205` SHA256 `f87210b01d3d5356bcc3784e47e9f64e786cc13efdaba39172ec264574f7ac20` contains `EXACT_HEAD=e254e55e57f54ea14906cec00c32bf7fb5c91569` and actual `WORLD_BLOB=db62c761a9b1f3364c951ad6ac82a71f3a71d84f`. Independent review of workflow found the expected hash literal had been accidentally **truncated to 36 hex digits** (`db62c761a9b1f3364c951ad6ac82a71d84f`). Thus the `test` assertion failed silently before `git apply --check`. This was not a patch failure or production source drift. Fix commit `3cd28ff1ce12d49065ee99254ebf4d3fcecdccaf` restores the exact 40-hex Git blob, no relaxation of integrity requirement. The original failed run and raw evidence remain preserved.
