# JEF WP-U1 current-chat lifecycle boundary — verified review checkpoint (2026-10-30)

**Scope:** review-only child PR #1175 of #1174, exact parent `917c2c7d9d717426facd0bc6f98b126af3a4ece3`. Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. No production merge or authority promotion.

## Defect, repair, and proof
- Original `jefoutcome.lifecycle(r, event_id)` read `events.id` globally; operator `:fastpolicy lifecycle <Event-ID>` exposed foreign chat stage and update IDs. `lifecycle_summary` counted every `ExperienceRecord` globally and applied `LIMIT` before any chat boundary.
- Preregistration commit `83f1b82f9266f458551af83f110e38df5b2b1ddb` preceded regression test commit `f82f688d21572289a0e421bb1e907a05a5990082`.
- **Original RED** GitHub Actions `40974550349` on test-only source head `28f3d36b512cb7fcf98808d7635e01533d874f17`: 17 focused tests, **3 expected failures** (foreign event not rejected, global count 4 instead of 3, empty new chat still 1). Original raw artifact ID `12941179909`, ZIP SHA256 `f1a365ef3a5234ca4a91c4c5afeb2de7599db1d3494aa68f66de3a99cfbaa073`, 18/18 inner SHA256SUMS, CRC clean. No setup/import failure.
- Source fix commit `baa21fa053791c3aa44b80e90fde4aeb16944333`, source blob `1c4d6eaae7bdc68785560c3fea4835e94749da6c`: require `events.session_id=r.session` on single-event lookup and SQL-join `packets→events` with session filter **before** limit on summary.
- **Exact-source GREEN** GitHub Actions `40974635042`: 17/17 focused PASS, 0 skips, `CANON/VENV/DEPS/PIP_CHECK/FOCUSED/COMPILE/PRIVACY/DIFF` exits all 0. Raw artifact `12941668249`, ZIP SHA256 `2872a7e9909c2610677ac0f92f43db8f55ad5e3759a9c7eb67e01d5b257dfc12`, 18/18 inner SHA256SUMS, CRC clean. GitHub remote re-fetch verified exact fixed source blob. Test exercises two actual sessions, direct/TTY reads, SQL limit, unknown IDs, empty chat, SQLite close/reopen, and no model worker.
- Independent logic review: event scope is enforced in SQL, not after global result truncation; current-session lookup raises before reading lifecycle stages or update IDs; `:open` and restart are tested. Other global reports are **not** asserted chat-local.

## Existing wider evidence and negative gates
- Parent #1174 full unfiltered CI `40973462353` ran 3360 tests, **2 historical frozen Run34/Run37 `native_source_or_catalog_changed` errors**, 11 skipped; remains RED. No exclusion or alteration of frozen historical source.
- This package has **no native C3, Redmi, STEP2, B3, Body-JEPA, LP3, World-JEPA or whole-system success claim**. Age-0 RECORD_ONLY, original approval boundaries and `jepa_weight=0` remain.
- No private material or source data included in GitHub; public privacy scan CLEAN.

## Ownership / resume
Current owner: GPT-6 automation review-only branch `codex/v13-jef-lifecycle-session-20261030-auto11i`; parent #1174 remains owned by its original chain. No force-push. Exact next commands on a fresh worktree:
`git fetch origin; git switch -c review-jef-lifecycle origin/codex/v13-jef-lifecycle-session-20261030-auto11i; cd v13/code; PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_jefoutcome_session_20261030 tests.test_jefoutcome tests.test_jef_operator_session_20261030 tests.test_contextos_operator_session_20261029`.
Prerequisites: Python environment with NumPy 2.2.6, psutil, PyYAML, Pillow, prompt-toolkit 3.0.52; for full suite also pinned torch 2.5.1+cpu, Transformers 4.44.2, PEFT 0.13.2.
Next independent package: fix lifecycle update provenance matching currently based on raw source-ID substring in JSON manifest (false stage promotion), using preregistered exact `source_ids` controls. Continue beyond this checkpoint.
