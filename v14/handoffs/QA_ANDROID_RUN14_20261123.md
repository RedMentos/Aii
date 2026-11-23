# QA & Android — whole-Canon checkpoint, 2026-11-23

## Exact source state

- Repository: `RedMentos/Aii`.
- Release-development branch: `gpt6/v13-private-remote-bridge-20261111`.
- Read-back base HEAD at start: `fb563d771fe2d493c4ec25abe94280981d24ef5c` (2026-11-23 12:46:30 UTC).
- The branch is not itself a release receipt. No master or historical Canon bytes were changed.

## P0 Redmi / real-chat evidence boundary

- Latest authenticated private PIPELINE_STATUS read available before this run: private issue #775, receipt at 11:14 UTC, reports auto-update enabled and runtime/dashboard UPDATED at `dfa3945b2bbfdb65d932db74e02f402435494e84`.
- That receipt predates current base `fb563d77`; current installed phone SHA is therefore UNKNOWN. A fresh read-only PIPELINE_STATUS request was created as private issue #813; no receipt had arrived at the last poll. No duplicate UPDATE_REQUEST was sent.
- Latest public-safe device evidence in #1904: last stored turn FINAL at 57.739 s total / 41.627 s TTFT / 38.945 s C3 prefill, 751 prompt tokens, 2 generated tokens; correctness UNKNOWN. B1/B2 remain TIME_BUDGET at 53.2/54.2 s and 0 valid offers in the latest five-turn aggregate. No new CHAT_SEND was performed.
- No current Android/Termux session, model residency, APK, microphone, UI capture/control, sustained PSS/RSS, 20-turn acceptance or new Redmi installation was tested. Keep `REDMI_UNVERIFIED` for current HEAD.

## QA implementation — M1 DATA test/ingestion regression

PR [#2444](https://github.com/RedMentos/Aii/pull/2444), branch `qa/v14-m1-data-ci-repair-20261123-run11`.

- Repaired double-escaped newline fixtures in `v14/m1/test_data.py` and `test_array_data.py`; malformed CSV tests now reach the intended timestamp/truncation checks.
- Corrected the strict-NaN affected-origin interval: with L=5, H=2, a missing row at 100 affects origins 98–104, not 96–97.
- Added `v14.m1.test_baselines` to the M1 workflow so persistence, seasonal persistence, train mean/median, Ridge-AR, LAD-AR and MAE tests actually execute.
- First repaired exact CI (head `8ab5c7182ca29aa028578b4b9f2b59a2b5f1aba7`): all DATA and baseline tests passed except direct-array/reference dataset fingerprint parity on Python 3.13 and 3.14.
- Root cause: `ArrayDataset.from_uci()` hashed literal backslash-n bytes, while `dataset_sha256()` hashed newline bytes. Changed the direct-array record separator to the same canonical newline; current PR head `15ff43f0aa6957f20e22cea3579bafaa90a81347`. Follow-up exact-head CI was pending at last read.
- Full local Aii checkout/tests: `NOT_RUN/BLOCKED` (no mounted checkout). No real UCI cohort, preregistered test-year access, training or weight update. M1 remains experimental.

## Independent integration QA

Boss source-forget composition PR [#2443](https://github.com/RedMentos/Aii/pull/2443), exact inspected head `32f2ce6e9195da5fd781a6a4e9564ec0862f97ba`, is NOT ready for merge:

- `staged-runtime`: 19 failed, 234 passed, 10 skipped, 2 errors.
- Exact nested-builder pin expected `cbc62ff7c4489517744c8d76b8ee0b58008604a8bee861d2375690495ff71b64`, actual `088b31a752b1db21872634f35c9491e58da52e13b251c8f66bc02f405bbfe050`; integrated deploy also reports `Integrated stage builder changed`.
- `record_only_controller_guard_20261116.py` is rejected as changed.
- Optimizer-resume (3.13/3.14), staged Python 3.14, Lab-Age, consumer, verify and staged audio/arithmetic inherit the pin mismatch.
- Old-phone migration separately returns PARTIAL / UPDATE / runtime ERROR even though both source checkouts reach the target SHA. This is not a successful staged activation.
- QA comment was posted on #2443 with the exact failures and required bottom-up pin/migration retest. No gate was weakened.

## Whole-Canon acceptance still open

- A0–A5: source-bound audio/vision/UI paths have partial producer/SHADOW work, but real Android microphone, MediaProjection/Accessibility, revocation and end-to-end perception remain unverified.
- B1/B2/C4/C3: native useful offers and same-turn consumption are not proven; #1904 P0 remains open.
- B3: production activation-to-activation learned latent receiver remains OFF; symbolic/JSON and synthetic probes are not latent acceptance.
- World/Self/Memory/JEPA: source-bound SQLite/NumPy paths and rollback guards exist, but persistent native body-weight update, held-out utility, retention and true unlearning are not accepted.
- Voice, Android background/API control, tool agency, sleep/replay, self-edit and full Canon consumer coverage remain incomplete or gated.

## Next QA actions

1. Poll exact PR #2444 head CI; fix any remaining M1 failure and keep it DRAFT until all three test modules pass on Python 3.13/3.14.
2. Recheck Boss #2443 after pin-chain and migration repairs; do not merge a red exact head.
3. Poll private issue #813 for the current installed SHA. Do not send another update request or manual Termux command; do not infer installation from GitHub CI.
4. Continue the whole-Canon evidence map, prioritizing actual B1/B2→C4→C3 and native chat correctness/latency once a consented device receipt/test path is available.

User action: none at this checkpoint. No chat send, log-page request, shell, model/weight swap, permission change or device mutation was performed.
