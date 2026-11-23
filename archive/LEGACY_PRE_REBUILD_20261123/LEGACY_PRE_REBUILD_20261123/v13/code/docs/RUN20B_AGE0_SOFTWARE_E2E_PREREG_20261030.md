# Run20B preregistration — Age0 end-to-end software integration on latest chain (2026-10-30)

Parent: Run20 review branch `assistant/v13-run20-resource-sensor-finite-20261030-hourly11` at `8672dbdd599b960c9c353c98853fb5d24b19fcf4` (after connected native workflow creation). This is a focused, **independent acceptance diagnostic**, not an Age promotion or replacement for unfiltered fullsuite. No code/model/seed changes; owner GPT-6.

Freeze test modules before execution:
- `tests.test_run82_age0_operator_e2e`
- `tests.test_run83_age0_backup_restore_e2e`
- `tests.test_age0_source_context_world_sleep_integration_20261029`
- `tests.test_age0_jef_f1f5_crossorgan_20261029`
- `tests.test_context_self_sleep_age0_20261029`
- `tests.test_run14w_context_world_effort_integration`
- `tests.test_worldmodel_realstore_integration_20261029`
- `tests.test_world_jepa_closedstore_private_pipeline_20261028`
- `tests.test_jefoutcome`
- `tests.test_step12`

Run in isolated Python venv, pinned `numpy==2.2.6`, no native/model downloads, fixed seed cohorts unchanged, Linux SQLite software only. Preserve all stage exits, full verbose raw and SHA256SUMS; do not hide failures. Explicitly check `V13_NO_AUTOSTART=1`, `NO_MODEL_DOWNLOADS=1`, privacy scan and diff. A GREEN result means only these selected end-to-end software contracts passed; it does NOT establish native/Redmi performance, STEP2 utility, B3, Body-JEPA, jepa_weight>0 or whole V13. The Run20 cumulative unfiltered and native workflows remain separate authoritative evidence paths. Backup raw privately and verify readback bytes.
