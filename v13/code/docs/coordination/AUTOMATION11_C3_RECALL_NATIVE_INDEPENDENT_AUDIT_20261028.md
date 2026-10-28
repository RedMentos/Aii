# Independent raw ZIP audit: actual Memory.recall → guarded C3 (2026-10-28)

**Review owner:** GPT-6, independent read-only artifact audit of #887. **Base/source:** `7b48d94eee00734891fef1fe1ac3eb360023c39a`, PR #887. This is a review child, not a production merge. Parent #885 software result 20 focused + 2289 full tests PASS, 1 skip; native workflow #887 [40660393285](https://github.com/RedMentos/Aii/actions/runs/40660393285) completed SUCCESS at the exact parent commit.

## Raw evidence closed and checked

- Downloaded Actions artifact **12803502784**, ZIP **SHA256 `a00d8d837ff703ec97eb3f3b2347af8959058fc15b78eaff485792603a51bdbd`**, size **16180 bytes**. Independent Python `zipfile.testzip()`: CRC clean; **24 ZIP entries**, 23/23 internal `SHA256SUMS.txt` entries match, no missing/duplicate entries. `HEAD.txt` matches `7b48d94eee00734891fef1fe1ac3eb360023c39a`.
- Verified all ten exit files equal **0**: BLOBS, INSTALL, COMPILE, FOCUSED, BOOTSTRAP, MODEL_VERIFY, NATIVE, REPORT_CHECK, PRIVACY, DIFF. Focused log **20 tests OK**; privacy log **CLEAN**. GitHub Actions job `122721678785` completed success; its workflow requires these exit files before success.
- Recomputed canonical fixture JSON SHA256 **`9aef60556396470a91d0684ce85151a1dfec112eca92be62485ae1d99d33fd93`**, matching the preregistered eight distinct synthetic project budgets (four EN/four DE). Seeds **cohort 2802029**, **native 13** unchanged.
- Independently checked every row, not only report-level booleans: positive **8/8** exact source-backed project amounts, baseline **0/8** exact, absolute paired gain **8/8**; all 16 actual C3 calls FINAL, correct pinned LFM2.5-350M model, each process reaped, model-before equals model-after, deep hash verification logged. Each positive has actual retrieved memory ID and SourceRef; no other project named in the answer. Negative 8 projects × 4 cases = **32 unique CLARIFY cases**, zero native calls, no prompt messages and no multi-digit amount leaked.
- Independent auditor rejected a deliberately modified `NATIVE_REPORT.json` ZIP (internal SHA mismatch) and a ZIP with `NATIVE_REPORT.json` missing. This verifies the audit detects corruption, **not** a general tamper-proof guarantee. The ZIP itself is retained as the immutable Actions artifact above.

## Findings and claim limits

**SCOPED_LINUX_NATIVE_PASS**, for isolated actual `Memory.recall` → SourceRef-checked C3 source consumption, not the frozen Runtime turn. The baseline without source invented unrelated amounts; the source-backed arm used explicit source data in its prompt. This does **not** establish general semantic recall, prompt-injection resistance beyond these bounded cases, sustained learning, body-model training, or reliable unscoped factual answering.

**Negative gates remain:** original 20-stage Stage11 FAIL; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA unavailable; LP3 heldout FAIL; `jepa_weight=0`; Age0 RECORD_ONLY; no Redmi thermal/RSS/KV/energy or retention promotion; no full architecture completion. No runtime/model/seed/fixture changes in this review branch.

## Reproduction / handoff

Source workflow: `.github/workflows/automation11-c3-recall-native-20261028.yml`. Prereg: `v13/code/docs/coordination/AUTOMATION11_C3_RECALL_NATIVE_PREREG_20261028.md`. Collector: `v13/code/scripts/native_c3_recall_consumer_heldout.py`. Exact raw ZIP: `https://github.com/RedMentos/Aii/actions/runs/40660393285/artifacts/12803502784`.

Independent local audit command: `python audit_v13_c3_recall_native.py c3-recall-native-40660393285.zip` (reviewer's local standard-library audit, not committed with this note). Observed: `INDEPENDENT_SCOPED_NATIVE_AUDIT_PASS`, 23 internal SHA, 10 exit stages, 8 positive, 0 baseline, 32 negative no-call, 16 native. Preserve raw ZIP rather than claiming the local script alone proves original run.

**Next authorized package:** investigate the still-unwired `render_messages` caller-authentication/dispatch boundary in a new isolated candidate and test a forged `ADMITTED` dictionary with syntactically valid but source-unbound `value` and `source_ref`. Current `verified_recall_messages` is guarded; the direct renderer accepts a dict, so do not treat it as an authorization API. Preserve original native source SHA when comparing, and do not promote this candidate without full software/native evidence. Independent path if blocked: Stage11 source-consumer integration, separate from original frozen runtime cohort.

**Remote persistence:** review branch owns only this audit note; parent PR #887 and other owners' branches remain untouched.