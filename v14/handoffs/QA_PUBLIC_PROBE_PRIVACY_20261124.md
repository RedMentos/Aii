# QA: native probe output privacy — 2026-11-24

The current release base still exposes the complete native smoke report through the interactive Runtime worker and one-shot probe CLI. The report contains C3 output, B1/B2 offer hypotheses and C2 control payloads. Probe exceptions can also leak exception text.

The proposed repair is a staged, source-pinned output boundary: keep the full artifact local, emit a closed-vocabulary numeric summary to the console, and replace probe error details with a fixed code. No raw V13 runtime source, models, SQLite, chat history or device state is changed.

Focused isolated tests are being prepared. Full staged/integrated CI and Redmi installation remain unverified. The last authenticated device state is STOPPED_BY_USER; no device action is authorized or performed.

## Delivery blocker
The branch commits and exact source readback succeeded, but GitHub rejected both pull-request creation attempts with HTTP 403: "At least one email address must be verified to do that." The push-triggered workflow also ended in startup_failure with no jobs, and GitHub would not retry that run. The code is committed on the QA branch but has no PR and no exact staged/integrated CI evidence yet. A verified GitHub account email (or an authorized alternate review path) is required before the PR/CI handoff can be completed.
