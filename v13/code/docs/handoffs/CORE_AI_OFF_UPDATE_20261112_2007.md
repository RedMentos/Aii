# Core handoff 2026-11-12 20:07 Europe/Berlin

- Owner: Core & Harness. Package: CORE-AI-DESIRED-OFF-UPDATE.
- Base phone release: `gpt6/v13-private-remote-bridge-20261111` at `f3d4a9cc839abda6a8c2a958d48648163c70a765`.
- Review branch: `gpt6/core-ai-off-update-20261112-2007`, PR #1863. Never claim released before Boss integration.
- Files: `v13/code/v13/lifecycle.py`, `v13/code/v13/chat_service.py`, `v13/code/tests/test_ai_off_update.py`, `.github/workflows/v13-ai-desired-state-update.yml`.
- Technical hypothesis from #1860: a pending lifecycle resume marker may revive the managed model after the user explicitly switched AI autostart OFF. Existing `ChatService.tick` called `service_resume` regardless of desired state. Cause of the observed Redmi ON/OFF difference is **not established**.
- Change: local desired-state is supplied to both tick resume call sites; disallowed resume consumes a stale marker and never calls `console.start()`. Explicit ON still works. No remote owner command can set the local desired state.
- Reproduction/tests: `cd v13/code && python -m unittest -v tests.test_ai_off_update tests.test_chat_service tests.test_pipeline_agent`; `python -m py_compile v13/code/v13/lifecycle.py v13/code/v13/chat_service.py v13/code/tests/test_ai_off_update.py`. Exact CI workflow committed. Local full checkout failed due DNS `Could not resolve host: github.com`; **not** a test pass. CI result must be checked on exact latest SHA.
- Privacy: no phone logs, user text, model data or credentials in this package. Synthetic/Linux CI is not Redmi proof.
- Gates: B1/B2 native TIME_BUDGET, STEP2/B3 negative results, JEPA SHADOW and all learning/permission gates unchanged.
- Next: check latest push CI, independently inspect OFF/ON race, run public privacy scan, ask Boss to integrate only after review and release CI. Then verify on Redmi using owner-approved technical PIPELINE_STATUS/DIAGNOSTICS and a locally initiated OFF->update->OFF reproduction. Do not request arbitrary shell or device privileges.
- Other core priorities: real B1/B2 stage-timing native profiling, actual C3/B1/B2 adapter update/retention, Android capability companion, voice decoder and persistent user-facing runtime; all remain open.
