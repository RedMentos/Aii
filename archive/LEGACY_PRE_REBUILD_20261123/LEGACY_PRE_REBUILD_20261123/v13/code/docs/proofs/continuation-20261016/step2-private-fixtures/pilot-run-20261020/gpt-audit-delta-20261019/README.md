# Isolated read-only audit candidate for the registered STEP2 private pilot

This is an additive proof-integrity tool, **not** a replacement for `runtime_adapter.py` and not a new preregistration. It must be reviewed before integration. The registered pilot remains exactly three fixed complementary A/B/NONE fixtures × six arms = 18 rows, maximum 42 native calls. Original historical STEP2 `UTILITY_FAIL` and B3 L1 `FAIL` are unchanged. No native models were executed by this candidate.

Copy `audit_private_pilot.py` beside the existing `pilot/` and `runtime_adapter.py` files, or invoke it by absolute path. It has no project imports and requires only Python standard library. From the **same exact registered source checkout** (`v13/code`):

```bash
python /path/to/audit_private_pilot.py \
  --registration docs/proofs/continuation-20261016/step2-private-fixtures/pilot/native-registration.json \
  --fixtures docs/proofs/continuation-20261016/step2-private-fixtures/pilot/pilot-fixtures.json \
  --source-root . \
  --installed-home /workspace/scratch/f24630d7727d/private16-pilot-home \
  --out /absolute/new-audit-preflight.json
```

Before inference this should report `PREPARED_NOT_RUN` only if the registration, fixture geometry, source bytes and all installed model/runner/library bytes still match. Missing original absolute model paths cause a refusal. Do **not** edit a registered path, overwrite a cohort or treat a structurally valid registration as native evidence. An independent installed cache must have the registered exact files; if that is impossible, stop and use a **new separately published registration**, not an unrecorded substitution.

After the existing `runtime_adapter.py run` completes in a **new** output directory, rerun with `--run-dir /absolute/finished-run`. The tool checks 18 ordered row files, hashes, FINAL calls, exact producer/consumer role order, one reaped release per call, and nonpromotion. `ARTIFACT_CONSISTENCY_PASS_NOT_QUALITY_GATE` is not an independent model-run attestation or a utility PASS. Raw outputs still need source-bound score verification and independent review. Do not re-run the same registration to fill missing rows.

Software tests:

```bash
python -m unittest -v test_audit_private_pilot.py
```

No external libraries or copied third-party code. No frozen V13 production or preregistered source file was modified in this candidate.
