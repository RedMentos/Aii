# V13 Redmi release handoff — 2026-11-12

This is an **operator-delivery contract**, not a new blueprint or licence to
skip proof. The user wants the five existing hourly ChatGPT development
automations to **write and test useful code**, and one trustworthy **Update all**
button on the locally running Android UI that installs their integrated work.

## Fixed release channel

- Development system of record: \`RedMentos/Aii\`.
- Current **phone release branch**: \`gpt6/v13-private-remote-bridge-20261111\`.
- Runtime Git clone on phone: \`~/.v13-runtime-source\`.
- Dashboard / relay Git clone: \`~/.v13-agent-source\`.
- Local data, models and DB: \`~/v13\`, **never reset or re-download them for a code update**.
- Actual launcher: \`~/v13/bin/v13\` — updated by
  \`v13/code/v13/runtime_deploy.py\`, not by \`git pull\` alone.
- Immutable active snapshot: \`~/.v13-runtime-builds/v13-<commit>-*/code\`,
  including source modules, scripts, specs and \`docs/canon\`.
- On-Redmi \`Alles aktualisieren (KI + Oberfläche)\` and automatic 15-minute
  polling use \`pipeline_agent.run_cycle()\`: exact branch, fast-forward,
  CI gates, graceful shutdown, staged source selftest, atomic launcher swap,
  service/UI refresh and automatic resume.
- Remote owner can **request** the same bounded update through a private
  \`V13READ\` / \`UPDATE_REQUEST\` issue; the phone runs only pinned local
  update logic. Do not introduce arbitrary GitHub-issue shell evaluation.

## Five-hourly-agent integration rule

The five genuine hourly automations are **Core & Harness** (:04), **Forschung
& Perception** (:00), **QA & Android** (:15), **JEPA & Memory** (:30), and
**Boss & Integration** (:45), Europe/Berlin times as configured.
They work in independent branches / PRs, preserve exact role ownership,
write synthetic tests and post durable GitHub commits.

**Boss & Integration owns the release train:** monitor other four and own
changes, review actual modified file paths, licences, code, tests and runtime
impact; cherry-pick/merge only compatible, reviewed changes into the fixed
phone release branch using fast-forward/pinned ancestry and conflict controls.
Never mark another role's draft PR as installed before it is on this branch.
CI must be green for that exact commit before a phone update is accepted.
Do not silently simplify the Canon, and do not mix speculative JEPA
weight-learning code with automatic activation.

Each specialist should explicitly report: **developer commit/PR**, synthetic
test, **merged phone release commit or NOT RELEASED**, Android proof status
(**UNVERIFIED** until on the actual Redmi), and one next runnable task.

## User-initiated phone issue report

The UI provides two one-shot private transmission buttons:

- \`Fehlerbericht jetzt senden\`: technical state, update state, bounded
  technical errors; no full transcripts.
- \`Fehler + Chat jetzt senden\`: also the last four recorded V13 console
  sessions and fixed service logs, bounded to a size limit.

The phone creates a \`V13PHONE:\` issue in **private**
\`RedMentos/Aiiii\` with chunked verified report pages. It never sends
GitHub credentials, private config, DB, GGUF weights, arbitrary folders,
or code to execute. Credentials and localhost session tokens are redacted.
The report is visible to the GitHub-connected assistant once created, but
**not automatically inserted into a ChatGPT conversation**. The assistant
must explicitly read the issue through the connected GitHub tool.
The request is not continuously open device control; the user can toggle
diagnostic sharing independently and stop the local relay.

All changes affecting local Android UI, background service, remote owner
commands and deploy must have offline regression tests. Real Android
hardware is the acceptance target, not a Linux-host CI proxy.
