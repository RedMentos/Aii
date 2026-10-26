# Run434 — next exactly one pinned Linux-native P_s21 arm (source-first)

Date 2026-10-26. Owner GPT. Stacked review-only on Run433/PR432 independent 168-row postflight checkpoint `0db3a569aa16dd495d6c4013b4610229fd03ed74`. No changes to frozen Run394/397 source, model catalog, runner, fixture/seed hashes, or prior native receipts.

## Verified prerequisite

Run427 producer Actions 40263042202 SUCCESS, 168 rows O/P/S_s20 + O_s21. Independent no-model Run433 Actions 40265361929 SUCCESS, both observed outer artifact SHA256 and Run430 atomic importer/Run429 independent verifier GREEN; 131 files, 85,615,998 bytes, manifest SHA256 bde79cc2b97fe58e252ace1cfaa800a2bcae1482e61ec23743f6f1423238668d. STEP2 remains UTILITY_FAIL. No parallel native owner observed after Run427 completion.

## New package

Source-only `run434_stage5_p21.py` must restore only Run429-verified actual 168-row no-model export to a fresh work directory, exclude the export manifest, independently revalidate each of the four prior 42-row native receipts against exact pinned runner/model/fixture identities, then and only with explicit `--execute` invoke unchanged `run397_step2_resume.run(...,pilot=False,max_new_arms=1)`. Exact next arm must be `P_s21`, 210 total rows, four arms remaining; wrong arm, missing/forged receipt, source/runner drift, failure, overlapping owner or false gate promotion must be RED and retained. Always safe-export partial/failed work when prerequisites allow; never upload weights or installed models. Source-only synthetic tests must not be presented as native evidence.

## Execution

After focused tests/independent review, queue **one** native Actions job with existing serialized group `v13-native-c3-run131-serialized`, `cancel-in-progress:false`; verify exact Run433 small raw + Run427 safe ZIP IDs/hashes and producer source, install pinned public models in isolated runner, run one arm. Native work is separate from source-only branch and can be long. A future independent 210-row postflight is required before S_s21. Preserve every failure.

## Negative gates

STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi unmeasured, Age/whole V13 incomplete.
