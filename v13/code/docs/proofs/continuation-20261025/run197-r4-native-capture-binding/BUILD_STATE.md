# Run197 — R4 source-bound future task manifest and offline native capture binder

## Source/ownership
- Parent: verified Run196 PR224 head `975df38b8ea164885784629be310694bf5b7022b`, itself based on Run195 PR223. New branch owns only `scripts/run197_r4_future_manifest.py`, `tests/test_run197_r4_future_manifest.py`, this evidence folder and new CI workflow. No frozen Runtime, native cohort, JEF, learning, Phone or Canon changes.
- Active native B2/C3 owner from Run189 is not overlapped. No native job was started.

## Implemented software path
- `manifest` calls the **actual full-checkout** `utility_bench2.tasks` generator for proposed future seeds `20261101/20261103`, plus historical seed7/seed11. It records each prompt SHA, expected number assertions and exact regex scorer, generator/scorer source hashes, and refuses duplicate future prompts or overlap with historical generator prompts. This checks exact prompt overlap only; not semantic novelty or exposure through other previous experiments.
- `bind` independently recomputes the full manifest from the pinned generator and scorer source, checks registered model/runner/source/capture-script hashes and exact registration hash, checks two 60-row raw capture hashes, verifies all fixture identities, untruncated output and token-stream agreement, recomputes original regex/number scores and checks token logprob feature consistency. It emits a Run196-compatible capture only if all checks pass.
- The binder is **offline** and does not itself establish that the raw capture was genuinely native or produced by the claimed model. That requires external native launch logs, binary/model SHA verification and independent provenance review before any use. A forged provenance sidecar alone is not proof. It never sets production authority.
- Run196 still requires a registration committed and verified **before** the native capture. No registration or new model capture was sealed or run in Run197.

## Tests and independent review
- First synthetic software suite 10/10 PASS (`tests_initial.log`). Independent review identified a provenance gap: a maliciously forged historical hash list could claim novelty. The binder now regenerates all prompts and scorer metadata from source; two new adversarial tests cover forged historical inventory and changed generator bytes. Final 12/12 PASS (`tests_final.log`).
- Full-checkout CI should also run the actual generator and both Run196+Run197 tests. No full-suite or official privacy scan has yet been observed in this local scratch.
- Evidence class `SOFTWARE_SYNTHETIC`; Linux-native and Redmi both NOT RUN. No new STEP2/B3/JEPA proof.

## Original gates unchanged
STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; DS2 H2 `FAIL`; full V13 `INCOMPLETE`. Run195 retrospective abstention remains `NOT_SUPPORTED` for deployment (compare stratum 7/10 wrong).

## Exact next steps
1. Independent full checkout review and CI; verify source hashes and run `cd v13/code && python -m unittest -v tests.test_run196_r4_stratified_future tests.test_run197_r4_future_manifest`.
2. Obtain pinned native model/runner/source hashes in a serialized native window; use actual manifest output and check semantic/historical overlap, then prepare and publish a sealed Run196 registration before any future native inference.
3. Implement registered native capture output (including complete answers, never silently truncate) and independently verify native logs/provenance; only then `bind` and `evaluate`.
4. Continue other disjoint canonical packages while native prerequisites remain unavailable.

## Commands
`cd v13/code && python scripts/run197_r4_future_manifest.py manifest scripts/utility_bench2.py scripts/utility_bench.py /tmp/run197_future_tasks.json`
`python scripts/run197_r4_future_manifest.py bind <sealed.json> <tasks.json> <raw-seed20261101.json> <raw-seed20261103.json> <provenance.json> <bound.json>`

## CI failure and follow-up correction (same Run197 branch)
- Initial GitHub Actions `40173724279` reported FAILURE. Local reproduction of `python scripts/run197_r4_future_manifest.py --help` with `PYTHONPATH` absent returned RC1 (`ModuleNotFoundError: No module named 'scripts'`); original stderr retained in `cli_initial.log`. This was a real direct-CLI import-path defect missed by the first 12 tests.
- Added explicit repository-root `sys.path` entry before importing `scripts.run196_r4_stratified_future` and an isolated subprocess CLI regression. Local 13/13 PASS (`tests_after_cli_fix.log`); GitHub CI rerun remains to verify after remote update. No native inference and no gate change.