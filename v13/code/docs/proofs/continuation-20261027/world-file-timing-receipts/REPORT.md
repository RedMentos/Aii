# Linux file-world row timing receipts — verified 2026-10-27

Review-only child of PR #655 exact `8322c9ac51501144ae57e5b0e39f204b203ae66b`, not main. Addresses an evidence reproducibility gap in PR #653's real Linux file-world → World-JEPA SHADOW checkpoint lifecycle.

## Concrete implementation
The previous exporter retained `cohort.json`, independent world schedule and process log but discarded each source row's `a0/a1` timestamps, preventing independent recomputation of `world`/`world_changed` labels. `validate_timing_rows` now requires finite ordered intervals, a nonempty chronological world log matching the schedule prefix (op/slot), and exact recomputed overlap labels before any export directory is created. The actual `main` path persists `row_intervals.json` with row index/action/time/labels and SHA256 in the manifest; `verify_timing_export` reopens all four persisted raw inputs after restart, verifies digests/row binding and recomputes overlap independently. Bounded read caps apply. The generic caller-supplied exporter remains unverified and cannot claim a timing receipt by setting a collection label alone.

This checks **recorded evidence consistency**, not cryptographic attestation of file mutations or causality. The source cohort hash is still computed from the original numeric/label rows; historical registered seeds/hashes are untouched. New source changes cause a new source digest only in new runs.

## Prospective RED / intermediate / GREEN
Prereg `de83c70cda9dcf7b3716e39c168f24a6bfb3e6b3`; tests `b4e3dd679be298e884b0337b16d3392859b1878b`; CI `7eaecd69a3ba6b1f724a174a05b7d44a1e04c11a`, all before source.
- RED Actions https://github.com/RedMentos/Aii/actions/runs/40450660382: **13 tests, 1 FAIL + 5 ERROR**, no timing validator/receipt; actual seed212 file-world subprocess export exit 0, read-only receipt verifier exit 1; compile 0, privacy CLEAN. Original ZIP artifact 12710012445 SHA256 `a13d138fac057cfbfc61b2537dd97d235fdcc83e2bdd794f49f2dc06f1c17c4e`.
- Intermediate source `18c5e647f740b5c2fa85c8c1f818aa3ac63f4af0`, Actions https://github.com/RedMentos/Aii/actions/runs/40450755161: **13 tests, 1 ERROR** (legacy mock schedule lacked required `at`), but actual seed212 file-world export and independent verifier both exit 0; compile 0, privacy CLEAN. Original ZIP artifact 12710142292 SHA256 `4f37c77bb3cc09e1b8989e691ed0d47a44864bf7499ccb9c6ef1058d095c43c0`.
- GREEN source+mock repair `852e0fd97a18e102902deca71677d908f655e14d`, Actions https://github.com/RedMentos/Aii/actions/runs/40450765823: **13/13 PASS**, real Linux seed212 file-world exit 0, read-only restart verifier exit 0, compile 0, privacy CLEAN. Original ZIP artifact 12710476829 SHA256 `63550413a6348f8f05dc625aeb358c8eddbd78a05c73371c34e862eb19ae669b`.

All original ZIPs CRC/HEAD/exit/SHA verified and privately backed up to `/V13-Checkpoints/2026-10-27/World-File-Timing-Receipts/`, then rematerialized and byte-verified. The rejected anyone-writable Drive location was not used.

The GREEN actual new unregistered Linux run observed **600 rows**, **119 clean calibration rows**, **16 independent process log events**, `row_intervals_sha256=20fb26a9f9541aabf1bb90363fd96c1090252af4081b4fbaf438ff892bfc7efb`, `cohort_sha256=ff6000deece3e4cc17dd180e7e640b137c89f4cf2ade1cf641fc73a95a7607de`; `verified=true` after persisted restart audit. This seed is nondeterministic at wall-clock/process scheduling level; its hashes are not substitutions for any original registered cohort.

GREEN source SHA256:
- `scripts/world_jepa_shadow_lifecycle.py`: `491133988f9a5b7433e822fae2b0c60e570a3c577e467f3ae62a6b770c045c74`
- `tests/test_world_file_timing_receipts.py`: `8276cc818bd88501be1809ff9bdd1687c3ba4d106c0b80607686f68391ac031e`
- `tests/test_world_jepa_shadow_lifecycle.py`: `fc4f71aaf950249c3c6f88e6448169b6070506e508d0938818d35f86b08eb626`

## Limits and next command
Software NumPy training on actual temporary Linux files/processes; not Redmi, not native LLM/Body weights, not semantic/causal World-JEPA utility. No automatic live observer, no model authority. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Age/approval unchanged, V13 incomplete. Main untouched.

Owner: next independent reviewer. Next: review the real-file timing consistency and move to an independent substantive blueprint package (e.g. current-chain full-suite triage or a source-validated runtime observation mapping), while full-budget v2 fresh-seed utility replication proceeds separately. Avoid another integrity-only loop.

Exact focused test (isolated NumPy 2.3.5 / prompt-toolkit 3.0.52):
```sh
cd v13/code
PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_world_file_timing_receipts tests.test_world_jepa_shadow_lifecycle
PYTHONPATH="$PWD:$PWD/scripts" python scripts/world_jepa_shadow_lifecycle.py --seed 212 --train 600 --steps 10 --output-dir /tmp/v13-world-new
PYTHONPATH="$PWD:$PWD/scripts" python -c 'from scripts.world_jepa_shadow_lifecycle import verify_timing_export; print(verify_timing_export("/tmp/v13-world-new"))'
```
Use a fresh output directory, never overwrite previous evidence.
