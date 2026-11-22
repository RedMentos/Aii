# Core handoff — explicit remote native-receiver probe allowlist (2026-11-22)

## Ownership and base

- Owner: Core & Harness
- Branch: `core/v14-remote-native-probe-allowlist-20261122`
- Base: `gpt6/v13-private-remote-bridge-20261111` at `b3b92f41772573732b2cba71f7ad6bf34dc8e521`
- Scope: unblock the already-staged, one-shot native receiver diagnostic through the existing private owner-read / CHAT_OPERATOR path. This does not execute the probe.

## Runtime change

The remote operator boundary now accepts one additional parameterized command, and only in this exact shape:

` :callosum native-probe <B1_DETAIL|B2_GIST> <B1_DETAIL|B2_GIST|C3_LANGUAGE> --last-source --confirm `

The actual accepted command contains one concrete sender and receiver role, has no angle-bracket placeholders, uses exactly one space between tokens, and requires distinct roles. The implementation is an exact full-match allowlist; no extra flags, shell operators, paths, source IDs, newlines, or alternate senders are accepted.

The same validator is used by:
- `remote_chat.send(..., operator=True)`
- private relay `CHAT_OPERATOR` HMAC command verification
- owner-read request creation
- owner-read request validation

The existing owner identity, private-repository, `CHAT_OPERATOR` permission, remote-test consent, one-shot request ID, bounded message size, and local operator's `--last-source --confirm` checks remain in force. Normal `CHAT_SEND` still rejects operator-prefixed text. No shell, arbitrary file access, model download, model swap, weight update, B3 production routing, or safety-permission change is added.

## Tests and environment

Added regression coverage in:
- `v13/code/tests/test_remote_chat.py`
- `v13/code/tests/test_remote_maintenance_bridge.py`
- `v13/code/tests/test_owner_read_bridge.py`

Expanded `.github/workflows/v13-private-remote-bridge-tests.yml` to run those suites plus remote-observation and patch-staging tests on Python 3.12 and 3.14, and compile the three changed modules.

- LOCAL_PYTHON_ISOLATED: PASS — exact role/flag regex, valid B1→C3 and B2→B1 forms, missing confirmation, same-role, C3 sender, extra flags, shell suffix and whitespace rejection.
- LOCAL_FULL_REPOSITORY: BLOCKED — no local checkout; container GitHub DNS lookup failed. No full local pytest run is claimed.
- CI: pending exact branch/PR run.
- TERMUX/REDMI: REDMI_UNVERIFIED — this change has not been installed on the phone and the native probe has not been sent or executed.

## User impact and canon

This unblocks a user-initiated, bounded measurement of the native receiver input path. A successful probe can establish native input consumption/effect for the tested model pair only; it cannot establish learned cross-model alignment, semantic utility, trained latent coupling, production B3 routing, or AGI.

No installed model, weight, permission, dataset, user message, or phone state was changed by this work.

## Next integration action

Boss/Integrator: review this PR and fold the verified allowlist + regression into the current release branch. After the release is actually installed and the owner has confirmed remote-test consent, the user may separately choose to issue the exact owner-read `CHAT_OPERATOR` request for one sender/receiver pair. Obtain a separate fresh `PIPELINE_STATUS`/diagnostic receipt afterward; do not infer phone execution from a GitHub merge or an `UP_TO_DATE` updater state.

## Proposed V14_USER_NEXT_ACTION update

`REMOTE_NATIVE_PROBE_ALLOWLIST`: implemented on this branch; awaiting independent review and release integration. Probe remains NOT_RUN. No user action is needed until release installation is verified; then ask for explicit approval before sending the exact one-shot command.
