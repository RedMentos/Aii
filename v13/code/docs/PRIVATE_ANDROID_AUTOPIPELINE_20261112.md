# V13 private Android auto-pipeline – 2026-11-12

Source: `https://github.com/RedMentos/Aii` (development branch `gpt6/v13-private-remote-bridge-20261111`). Private relay: `https://github.com/RedMentos/Aiiii`.

## Actual wiring

1. GitHub developers/agents push a code change to the tracked V13 branch and publish test results.
2. The independent Termux **owner-read bridge** on Redmi checks the private repository roughly every 45 seconds and (after opt-in) invokes the `pipeline_agent` automatic update check every 15 minutes, **even if Brave/browser is closed**.
3. The updater compares Git commits in two independent, existing checkouts: V13 runtime `~/V13-Phone` and browser/relay `~/.v13-agent-source`. It only downloads Git deltas and permits fast-forward on the already selected branch, refusing modified tracked files or changed remote/origin.
4. For dashboard/relay updates, the exact target commit must have **successful completed** `V13 private owner-read Termux bootstrap` and `v13-private-remote-bridge-tests` workflows. Runtime updates additionally require `V13 staged context and integrated regression`, also green on that same commit. Unverified, in-progress, failed or missing CI **blocks** automatic updates. Phone checks the exact `head_sha` and original repository.
5. When V13 is running, **no executable source is swapped**. The cycle records `BLOCKED_RUNNING` and retries later. The updater does not touch `~/v13` models, memory or chats, does not execute migration scripts, and does not grant an AI arbitrary shell or Android controls.
6. When the dashboard/relay source is updated, private refresh markers allow the running UI to restart on the same `127.0.0.1:18713` URL after V13 has stopped, and the bridge to re-exec after its current private issue poll transaction. The previous Git revision remains available for rollback, with syntax validation.
7. A bounded technical status `~/.v13-private/pipeline-status.json` records `AUTO_OFF`, `UP_TO_DATE`, `UPDATED`, `CI_WAIT`, `BLOCKED_RUNNING`, `ERROR` and component states. It contains no tokens, file contents, private chats or raw traceback text.
8. The **Wartung** tab shows this live status and has **Auto-Updates EIN/AUS** and **Auto-Pipeline jetzt prüfen**, alongside manual controls. Only the first setup enables auto by default, as requested by the owner; later OFF choices are remembered.

## Full remote ChatGPT/agent loop

The private GitHub connector can create an owner-authorized short-lived issue:
- Title: `V13READ:<32 lowercase hex id>`.
- Body: `{"schema":"v13.private-relay.owner-read/1","id":"<same id>","command":"PIPELINE_STATUS","expires_at":<Unix time within 600 seconds>}`.
- A trusted `RedMentos` issue author and exact private relay are mandatory. The mobile bridge signs the command locally with its secret; that secret does not enter ChatGPT or GitHub.
- The response is a private issue comment with recorded pipeline state, and the issue is closed. `DIAGNOSTICS` additionally returns allowlisted native model status and, **only after separate local UI opt-in**, a redacted/bounded excerpt of console errors/text. Unrecorded old Termux scrollback is not readable.

The existing hourly **V13 Boss & Integration** automation has been updated to request/check this private status, compare current GitHub tests and diagnose problems. It must not claim live phone proof without a receipt and should continue code fixes in its GitHub workflow. This is **not** permission for unreviewed AI shell commands, app UI operation or external data uploads.

## Extended private diagnostics – paginated V13/Bridge/Steuerzentrale logs

The user specifically requested direct remote troubleshooting rather than manual Termux copy/paste. The verified owner-read protocol now accepts an additional **LOG_PAGE** read-only request on the PRIVATE `RedMentos/Aiiii` repository:

- Title: `V13READ:<fresh 32-hex request id>`.
- Body: `{"schema":"v13.private-relay.owner-read/1","id":"<same>","command":"LOG_PAGE","expires_at":<Unix +600sec>,"args":{"session":0,"page":0}}`.
- `session` 0–31 refers only to the most recent recorded **UI-started V13** sessions, newest first; 32 is the maintained private `bridge.log`; 33 is the maintained private `ui.log`. `page` 0–2047 counts bounded 2400-byte chunks from the **end** (most recent logs first). Response reports `session_count`, `total_pages`, `kind`, `page`, status and redacted `text`. No caller-provided file paths, shell, arbitrary OS process/log capture or permissions outside explicit owner-read scope.
- This requires the user to click the separate **Konsolentext TEILEN** toggle on the local V13 UI. **OFF by default**, and turning it OFF makes subsequent LOG_PAGE calls return `USER_NOT_OPTED_IN`. V13 user input lines and recognizable tokens/emails are masked, but generated model output may still contain sensitive context; the private GitHub service stores the resulting issue comments. If the user declines sharing, a local ZIP remains an option.
- ChatGPT's connected GitHub interface and the hourly Boss task can retrieve pages, diagnose phone-side errors, and write fixes to the source branch. This is *not* unrestricted automatic remote control. The Android app must be alive to poll the private inbox.
- Other Termux sessions that were not launched/captured by V13 and already-lost scrollback cannot be obtained. Never promise all future raw shell activity is observable.

## One-time migration on the Redmi

The old bridge does not yet know `PIPELINE_STATUS` and cannot update itself without at least one local setup refresh:

```sh
curl -fsSL https://raw.githubusercontent.com/RedMentos/Aii/gpt6/v13-private-remote-bridge-20261111/v13/code/scripts/termux_one_command.sh -o "$HOME/v13-start.sh" && bash "$HOME/v13-start.sh"
```

This reuses the existing GitHub login, private HMAC key, and models. It downloads the new bridge and pipeline module, starts the background poller, and opens the single fixed-address phone UI. It will not destroy active chats: the installer refuses to run if V13 is still active.

## Proof and limitations

- GitHub Actions tests the exact-commit CI-gating logic, rollback, UI/bridge command validation, source update simulation and state/status privacy.
- **Android runtime auto-update has NOT been verified on the physical Redmi until it installs this new version and an actual pipeline cycle produces a private `PIPELINE_STATUS` receipt.** Linux CI is not a substitute.
- Android can stop Termux due to battery optimization or after reboot. The installer now also creates an owner-only optional `~/.termux/boot/v13-private-relay` hook. It starts the relay automatically after a reboot **only if the separate official Termux:Boot Android add-on is already installed/activated and auto-updates are locally enabled**. It does not hold a wake lock, does not open a browser, and never overrides the local STOP switch. Battery restrictions and reboot behavior still require a real Redmi test; this is not an uninterruptible cloud agent.
- The user's local V13 learning, JEPA, native model runner and overall blueprint completion remain separate and incomplete in areas reported by their real diagnostic probes. A successful updater is not completion of V13 itself.
