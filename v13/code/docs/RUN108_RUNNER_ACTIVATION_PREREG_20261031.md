# Run108 / Native runner activation rollback — preregistered 2026-10-31

Owner: GPT-6 continuation. Review-only child of Run107 PR #1476, exact parent `5d816feda3469a5149ab73e59116ef785a272848`. No production merge, no change to Canon, pinned b10964/model/seed hashes, or original evidence.

## Problem observed before code
Current `v13/bootstrap.py:install_native` promotes the new `llama-server` symlink before checking `--version`. On a nonzero exit or timeout, the previously usable live runner may be replaced while `runner.json` remains old. The pinned tar extraction/build destination is also reused across updates, so retry may overwrite the target of the existing symlink before validation.

## Fixed candidate and tests
- Stage each native candidate in a unique local `home/bin` directory; do not mutate the existing live runner's target before candidate validation.
- Check candidate executable, `--version` exit, and SHA before publishing. Promote a new symlink and manifest with explicit rollback on manifest-write failure, preserving existing symlink/regular-file runner and previous manifest. Never claim power-loss atomicity across two files.
- New model-free regression tests: successful promotion, version failure, timeout, injected manifest-write failure (symlink and regular legacy runner), no-old-runner failure, and staging isolation. Use actual temporary files and executable shell fixtures; mock only external build/download and injected failure.
- Run focused tests and the original 11 `test_bootstrap_safe_tar_20261031` regressions; compileall; check privacy/diff. If CI is possible, run pinned Linux Actions at exact HEAD with original raw logs, exit receipts and SHA256SUMS. Do not execute native models or run on Redmi; a fake version shell executable is not native model proof.
- Preserve Run105 original full-suite RED (4893, 5 FAIL, 64 ERROR) and all negative gates. If test-only implementation fails, retain RED and correct separately.

Next on success: inspect exact-head original evidence, then move to an independent functional C3/Body/JEPA package or Redmi installation readiness. This is a bounded installer reliability fix, not STEP2/B3/Body-JEPA utility proof.
