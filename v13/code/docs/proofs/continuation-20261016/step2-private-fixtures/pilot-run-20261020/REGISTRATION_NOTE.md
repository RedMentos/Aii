# Second, separately published pilot registration (2026-10-20, Claude thread)

The original `pilot/native-registration.json` (GPT/Codex, sha256 `321a074b…`) cannot be run
here: `run_registered()` re-creates the registration and requires byte equality, and it binds
GPT's container (`device`: Python 3.12.14, 9 CPUs, other kernel string; absolute paths under
`/workspace/scratch/f24630d7727d/…`; its own `config/models.json`). Editing it would be an
unrecorded substitution, so it stays untouched and **REGISTERED_NOT_RUN**.

`native-registration-20261020.json` (sha256 `2f0cd6f9…`, canonical digest printed by
`register`) was created **before any inference** from the exact registered source tree
`a1973d4` (`audit_private_pilot.py --source-root` = 0 errors) and a fresh installed home
built from the pinned catalog. Differences to the original registration, field by field:

| Field | Original | This registration |
| --- | --- | --- |
| device.cpu_count / python / platform | 9 / 3.12.14 / Linux-6.18.44 | 4 / 3.13.16 / Linux-6.18.44-fc-v139 |
| model + runner absolute paths | GPT scratch home | `/home/user/v13-pilot-home/…` |
| models_manifest_sha256 | `3c14f753…` | `71efdcc4…` (own config/models.json) |

Identical: all 3 model SHA256 + revisions (B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B, C3 LFM2.5-350M),
runner `llama-server` b10964 sha256 `79e31218…`, all 39 runtime-library hashes, all source
bindings, fixtures sha256, config, 18-row order, token caps, 90 s row deadline, empty
native environment. Scope stays `THREE_COMPLEMENTARY_CASE_DIAGNOSTIC_NOT_FULL_STEP2`,
no gate promotion, historical STEP2 `UTILITY_FAIL` unchanged.

GPT's read-only auditor (Drive `V13_PRIVATE_PILOT_AUDIT_RUN7_DELTA_20261019.zip`, zip sha256
`0646cd85…`, all 10 manifest hashes verified) is integrated beside the adapter as
`audit_private_pilot.py` + `test_audit_private_pilot.py` (11/11 OK). Its original delta
documents are kept in `gpt-audit-delta-20261019/`.
