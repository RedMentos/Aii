# Research/Perception handoff — 2026-11-20 08:55 Europe/Berlin

Owner: Research & Perception. Ticket V14-005. Existing PR #2118, branch `research-perception/v14-readonly-model-probe-20261120`.

## Changed source and exact remote checkpoint
- `v14/experiments/model_probe.py`: exit code zero is no longer labeled PASS. Read-only stdout capture (bounded to 64 KiB), visible output check, optional exact answer grade, no transcript printing, timeout and process failure remain distinct.
- `v14/experiments/test_model_probe.py`: negative cases for empty stdout, wrong arithmetic, prompt echo, nonzero exit, timeout, resource limits, and a synthetic answer-producing shell runner.
- Latest commit after updates: `e6732f2cf61af1674f7b3c11df7b39135f66ade8`; GitHub contents readback performed for test file. Earlier implementation commit `671aaf85329fc29f57a80587436c12f2250fed5f`.
- This is **not** a trained model, Android fix, deployed feature or native benchmark.

## Execution evidence and blockers
- LOCAL_LINUX exact-checkout tests: BLOCKED. Attempted `curl -L --max-time 12 -fsS https://raw.githubusercontent.com/.../model_probe.py`; DNS error `Could not resolve host: raw.githubusercontent.com`. Local environment therefore did not run the committed Python files. CI: NOT_VERIFIED. Redmi: REDMI_UNVERIFIED; no phone read receipt. RELEASE: NOT_RELEASED.
- A successful fake shell probe is only synthetic process/output validation. Real GGUF correctness, TTFT, RSS/PSS, thermal and B1/B2→C3 consumer still need native tests.
- The conservative exact-answer grader can mark a semantically correct verbose answer wrong; this is deliberate for strict `2+2` gate. Prompt echo stripping and CLI formatting require validation with the pinned llama.cpp revision.

## Next owner/reviewer actions
1. QA or Core checks out exact PR SHA, runs `python -m unittest discover -s v14/experiments -p 'test_model_probe.py' -v`, and repairs any FAIL.
2. Run pinned native llama-cli with registered local GGUF, record `NO_VISIBLE_OUTPUT`, `ANSWER_CORRECT`, `ANSWER_INCORRECT`, `TIMEOUT` separately and compare cold/warm timing, without raw text publication.
3. Boss/QA review PR #2118 before merge; only a validated, approved release may go through rollback-capable updater. Do not replace weights or models.
4. Continue broader V14-006 perception A5→B/C runtime integration and V14-003 latent receiver proof after coordinating file ownership.

No user action required for repository development.
