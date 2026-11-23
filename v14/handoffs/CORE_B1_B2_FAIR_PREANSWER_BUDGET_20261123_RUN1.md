# Core handoff — fair same-turn B1/B2 pre-answer budget (2026-11-23, Run 1)

## Ownership and exact base

- Owner: Core & Harness
- Repository: `RedMentos/Aii`
- Branch: `core/v14-fair-b1-b2-preanswer-budget-20261123-run1`
- Exact base: `gpt6/v13-private-remote-bridge-20261111` at `8d93236c753f0194224c19edc7411d8d7082b1d6`
- The older #2338 candidate was not merged or used as a stale branch. Its narrowly scoped fair-slice changes were re-composed onto the current release-development HEAD.
- This is a candidate branch, not a release. No V14 master, historical V13 Canon bytes, installed models, weights, permissions, Age, or phone data were changed.

## Defect and runtime effect

The short-turn recovery path could reserve C3's remaining native time by deferring every pre-answer B1/B2 pass. The sequential scheduler also gave the first body the entire remaining observer deadline, and the post-commit observer path ran only when no body had produced an offer. A successful B1 offer could therefore suppress B2 entirely.

This branch changes the existing runtime path:

1. C3 recovery now uses strict native evidence: `generated_tokens` must be an actual integer; boolean `false` is not accepted as zero-token proof, and a FINAL turn resets recovery only when C3 generated a positive integer token count.
2. The whole-turn observer window remains capped by the existing C3 reserve.
3. Sequential B1_DETAIL and B2_GIST receive fair per-role deadlines. Early completion returns unused time to the next role.
4. Cognition attempts a source-bound offer whenever its own remaining slice is at least 1.0 s; it defers only when that role's slice is below the minimum.
5. After FINAL, only a body that did not already produce an offer may receive the existing bounded post-commit observation. That observation cannot change the committed answer.
6. B1/B2 role identity, peer-message path, cancellation, parallel-residency policy, Age and learning authority remain unchanged.

The existing staged C4 source-validation/receipt and C3 same-turn consumer path is preserved. This change does not claim learned native latent coupling, successful native GGUF offers, or correct Redmi output.

## Files changed

- `v13/code/v13/native_turn_budget.py`
- `v13/code/v13/cognition.py`
- `v13/code/v13/observer_schedule.py`
- `v13/code/v13/runtime.py`
- `v13/code/v13/store.py`
- `v13/code/tests/test_native_turn_budget.py`
- `v13/code/tests/test_observer_schedule.py`
- `.github/workflows/v13-integrated-context-stage-20261111.yml` — now explicitly runs the scheduler regression

## Verification boundary

- Exact-head GitHub CI: pending; staged Runtime, integrated regression and the newly explicit observer-schedule test must pass before acceptance.
- LOCAL_LINUX full repository tests: BLOCKED / NOT_RUN. No Aii checkout is mounted, and `git ls-remote https://github.com/RedMentos/Aii.git` fails because this container cannot resolve `github.com`. No local full-suite PASS is claimed.
- TERMUX/REDMI: `REDMI_UNVERIFIED`. No fresh authorized device receipt was requested for this candidate; no chat send, update request, shell, APK install, pairing, permission change, model/weight swap or device mutation occurred.
- Runtime tests use a real Runtime/Store with fake C3 output and bounded offer seams; they are not native GGUF inference or phone performance evidence.

## Risks and next action

- The fair scheduler makes both pre-answer attempts possible under the existing reserve; it does not prove either native body returns a valid OfferPacket before its slice expires.
- Exact acceptance still requires correlated per-turn evidence: native input tokens and generated tokens per body, source-bound OfferPacket IDs, C4 selected IDs, C3 consumed IDs, TTFT/prefill/generation, and no regression in the C3 deadline.
- Next: poll this branch's exact CI, fix failures on this branch, then request independent Boss/QA review. After release integration, use the existing consented private owner-read path for a fresh Redmi turn; do not infer installation or user-visible improvement from CI.
- Shared-board ownership: Boss/Integrator should now update `V14_WORK_BOARD.json`, `V14_LIVE_WORKPLAN.md` and `V14_USER_NEXT_ACTION.md` with this exact branch/head and pending evidence; Core will not overwrite the concurrently edited shared-status files.
- User action: none required at this checkpoint.
