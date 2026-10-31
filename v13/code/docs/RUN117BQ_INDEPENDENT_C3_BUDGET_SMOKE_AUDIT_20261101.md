# Run117BQ — independent Run117BP native smoke receipt audit (2026-11-01 UTC)

Review-only child of Run117BP at exact source parent `753ea98a10400e3469fb4926e727742e8fe55c61` (itself child of Run117BO PR #1546). Do not merge or overwrite the active Run117BP owner. Canon v10.16.1 Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` and frozen Run46B seed401 fixture SHA256 `8aa69cc86d2e2067e809d4f703ddbff3fc575ea111d7afd97a73012e0bda0e21` unchanged.

## Purpose and implementation

Independent read-only stdlib `scripts/run117bq_independent_budget_smoke_audit.py` checks a future original Run117BP `report.json` against frozen fixture, pinned C3 model/runner SHA and revision, six exact ordered source cases, row hashes, native FINAL/reaping receipts, Store source recheck flags, prompt/candidate/output hashes, exact strict typed JSON including NONE/null, expected oracle, no oracle field in native prompt, zero-authority gates and absence of exported model weights under the supplied evidence root. No production wiring, no training or native call.

The auditor deliberately returns `AUDIT_STRUCTURAL_PASS_NO_NATIVE_ATTESTATION` even for a structurally perfect synthetic self-report. A JSON receipt cannot attest to a native process or independent generalization by itself. Original GitHub Actions raw ZIP, SHA256SUMS, job stage exits, pinned runner/model evidence and external verification remain separately required. Any mismatch returns `AUDIT_RED`. It does not alter Run117BP scores, labels, source, fixture, thresholds or original failures.

## Tests and scope

Seven local adversarial stdlib unit tests passed: synthetic self-report limited claim; forged FINAL; absent release receipt; wrong/duplicate JSON; fake model pin; promoted STEP2; injected oracle prompt field; wrong JEF candidate; swapped row order; changed row hash; predictor.pt export. Local execution was in an isolated scratch container with no model or Redmi. GitHub Actions workflow `v13-run117bq-independent-native-smoke-audit.yml` runs the same tests with exact Git blob pins, py_compile, public privacy scan, diff check and closed raw SHA256SUMS. Original Actions evidence must be checked before claiming CI success.

## Exact next command and gates

When Run117BP native artifact exists and its raw bytes are independently verified:

```sh
cd v13/code
python3 scripts/run117bq_independent_budget_smoke_audit.py --report /verified/native/report.json --fixture docs/fixtures/run46b_jef_source_eligibility_seed401.json --root /verified/native
```

Owner: Run117BQ independent review branch, distinct from Run117BP native owner. Next: audit the terminal original native ZIP, independently validate hashes/stage exits, privately checkpoint original raw and audit output, then preregister a **disjoint** cohort if warranted. Do not infer native execution from the synthetic tests or the self-reported JSON alone. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight=0; no Redmi, output, tools, learning, or whole-system completion. Remaining platform budget UNKNOWN.
