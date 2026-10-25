# Run266 first ephemeral patch preflight failure (2026-10-25)

- GitHub Actions run https://github.com/RedMentos/Aii/actions/runs/40186212183, job `121147430029`: **FAIL**, exit 1 before isolated Python deps and before focused tests; no candidate result and no native execution.
- The original preflight combined a Git blob equality assertion with `git apply --check` under `set -e` but did not log intermediate values. The job log shows exit 1 without patch stderr; exact failing assertion was not independently identified. The full GitHub job log is preserved; no raw artifact was created.
- GitHub connector independently read PR266 and PR261 `world_model.py` blob `db62c761a9b1f3364c951ad6ac82a71f3a71d84f` byte-identically. A locally reconstructed patch context passed `git apply --check`, but that is not a GitHub checkout proof.
- Fix commit `4667c03b839a114fb53cbecb540d4568794c073b`: explicit exact PR head checkout, record `EXACT_HEAD` and actual `WORLD_BLOB` in `RUN266_PRECHECK.log`, run verbose `git apply --check`, preserve precheck in raw artifact. Do not alter owner production source or relax SHA assertion.
- Next: inspect corrected CI. If source or patch differs, stop and report exact bytes instead of patching blindly. All original negative gates unchanged.
