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

## Verified software checkpoint

Actions **41252788638 SUCCESS** at exact source HEAD `328b520f3c5e9b7f704d598ec0379da9ed98ba6c`, artifact **13062325697**, original ZIP SHA256 **`39c7666682d8c2fb91e463d6d6471395a5256e17cae5ffe53158dc937c532762`**. Independently downloaded and checked ZIP CRC PASS, **12/12** inner SHA256SUMS, **5/5** stage exits zero, **7/7** adversarial tests PASS, privacy CLEAN, `git diff --check` PASS. Original raw privately saved to `/V13-Checkpoints/2026-11-01/Run117BQ-Independent-Audit/ORIGINAL_SOFTWARE_41252788638_sha39C76666.zip` and re-materialized with identical SHA256. This is software/synthetic proof only, **not** a Run117BP native result. Native Run117BP owner remains separate; do not start competing heavy jobs.

## Second package: persisted SQLite USER source proof (v2)

Extended independent auditor to read each `home-<id>/data/db/brain.sqlite3` in read-only mode and verify the latest two authoritative USER EventEnvelopes, same session/generation, exact SourceRef lineage, `sources` rows, original blob SHA256 and full text against the frozen prior/current fixture. If `--root` is supplied and the original native evidence lacks a persisted Store or source blob, audit fails RED rather than silently trusting report self-claims. Added missing-Store and blob-tamper tests. Local 9/9 PASS. Original first v2 Actions **41252954522 FAILURE** due test import from scratch package path; original failed ZIP SHA256 `decf4b1c2f063dbd77e6fbc3abe466cba9d5a2f7275515a9c114732694fbd134` preserved. Fixed import and pinned workflow; **final Actions 41253006941 SUCCESS** at source `b67c62a4d6046b888de58eaddfb252b0a9ad5f28`, original artifact **13061966534**, ZIP SHA256 **`19d9bf98cddc2a4d0229146133a08a8730c790c7275fd33e2e9e49055edc1c66`**. Independently downloaded: CRC PASS, 12/12 inner hashes, 5/5 stage exits zero, 9/9 tests, privacy CLEAN. Both failed and final ZIP privately backed up; final ZIP re-materialized byte-identical. No native C3 proof from synthetic tests. Next: independently audit original Run117BR native raw, if it becomes terminal; avoid overlapping heavy owners.
