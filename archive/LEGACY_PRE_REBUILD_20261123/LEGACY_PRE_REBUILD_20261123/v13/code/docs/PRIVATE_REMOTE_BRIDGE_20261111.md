# V13 private AI ↔ Redmi diagnostic / patch bridge — runnable preview

**Scope:** Actual source-only client, outbound Termux poller, authenticated GitHub Issues commands, sanitized diagnostics, private results, Ed25519-signed source bundle publication/staging, and optional single-source-file apply. Not a public SSH server, not unrestricted shell, not Android OS privileged access, and not native Redmi verified. Does **not** modify model GGUF weights or hot-reload the running Python process.

**Important:** `RedMentos/Aii` is the **public developer source**, **never the private relay**. Create a *separate PRIVATE* GitHub repository such as `RedMentos/v13-private-control` yourself and grant chosen AI accounts/apps access. The bridge checks the remote repo is actually private on every poll and before publishing anything. GitHub repo *URL* is the link; **fine-grained token + per-agent 256-bit HMAC key** are the credentials (not a human password in a URL). Do not paste tokens or HMAC keys into chat, a public issue, source repository, screenshots or model memory.

## Capabilities

| Command | Real effect today | Extra local requirements |
|---|---|---|
| `HEALTH` | Termux OS disk/memory/load and allowlisted local runtime status | Read-only, installed root exists |
| `LEARNING_STATUS` | Read-only numeric/symbolic organ status from explicitly configured *local* status JSON | Runtime must publish it; otherwise reports `UNINSTRUMENTED`/`UNAVAILABLE` honestly |
| `PATCH_STAGE` | Download private signed patch bundle pinned to a private relay commit, verify SHA, Ed25519 signature, exact existing file SHA, and matching code in public developer source commit; stage only | Trusted per-agent public key file + local `installed_commit` |
| `PATCH_APPLY` | Above checks, plus optional **one-file** atomic source replace with original-file backup | Local `remote_apply_enabled=true` and exact file in `apply_paths`; running process reports `RESTART_REQUIRED` |

Remote arbitrary commands, remote shell, reading user chats, generic filesystem read/write, automatic model training, unattended Android service startup, and Android permissions: **not implemented**. A live-running Python process may continue with old imports until the controlled restart is added. This is a deliberate honest limit, not a completed full remote desktop.

## One-time private setup (user/device owner)

1. Create a separate **PRIVATE** GitHub repository. Enable Issues. Grant only authorized agent GitHub accounts/apps access. Create a fine-grained token limited to **this private repo** with metadata read, Issues read/write and Contents read/write. Store token in the local shell/credential manager; never in public source. The same token account must be allowed to create/close issues. Agents can instead have distinct fine-grained credentials restricted to the same private repo.
2. Install V13 source that includes `v13/code/v13/remote_maintenance_bridge.py` and `termux_patch_staging.py`. In Termux install Python, Git and the official compatible `cryptography` package needed by Ed25519 signing/verifying. Keep Android power/background restrictions in mind; `serve` needs a running process and an internet connection.
3. Create a private directory with `chmod 700 "$HOME/.v13-private"`. Store config at `$HOME/.v13-private/remote.json` with `chmod 600`, and a **separate** public-key trust file. The locally generated per-agent HMAC secret is a random 32-byte key encoded in 64 hex digits (`python -c 'import secrets;print(secrets.token_hex(32))'`). Do not hardcode real keys in public GitHub. The Ed25519 private signing key stays on a **developer** machine, not on the phone or public GitHub.

Configuration example (all placeholder paths/names/keys must be replaced, do not use literal examples as secrets):

```json
{
  "relay_repo": "YOUR_ACCOUNT/YOUR_PRIVATE_RELAY",
  "source_repo": "RedMentos/Aii",
  "installed_root": "/data/data/com.termux/files/home/V13-source",
  "installed_commit": "0000000000000000000000000000000000000000",
  "state_dir": "/data/data/com.termux/files/home/.v13-private/bridge-state",
  "staging_root": "/data/data/com.termux/files/home/.v13-private/bridge-stage",
  "trust_file": "/data/data/com.termux/files/home/.v13-private/agents-public.json",
  "status_file": "/data/data/com.termux/files/home/.v13-private/live-status.json",
  "keys": {"agent-core": "REPLACE_WITH_64_HEX_RANDOM_SECRET"},
  "authors": {"agent-core": ["YOUR_AUTHORIZED_GITHUB_LOGIN"]},
  "permissions": {"agent-core": ["HEALTH", "LEARNING_STATUS", "PATCH_STAGE"]},
  "remote_apply_enabled": false,
  "apply_paths": [],
  "poll_seconds": 45
}
```

For a Git checkout, the bridge reads the actual `git rev-parse HEAD`, not merely the configured commit; the installed source cannot be replaced by a guessed Git SHA. For a source-only ZIP without `.git`, the locally pinned `installed_commit` is required and signed per-file preimage hashes are also checked. `installed_root` points to the folder containing `v13/code/v13`, not merely its `v13/code` subdirectory.

Run in Termux from the repo's `v13/code` directory, after exporting the private-repo credential:

```sh
export V13_RELAY_TOKEN='GITHUB_FINE_GRAINED_PRIVATE_REPO_TOKEN'
python -m v13.remote_maintenance_bridge once --config "$HOME/.v13-private/remote.json"
python -m v13.remote_maintenance_bridge serve --config "$HOME/.v13-private/remote.json"
# To stop remote intake from a different local Termux terminal:
python -m v13.remote_maintenance_bridge stop --config "$HOME/.v13-private/remote.json"
# To permit reads again:
python -m v13.remote_maintenance_bridge resume --config "$HOME/.v13-private/remote.json"
```

Do not actually paste a GitHub token into a command recorded in shell history; the sample shows the variable expected, not the recommended secret-loading process. Read from a private secret file or a credential store instead. A shell/process running `serve` is required; this release does not install an Android boot or foreground service.

## Authorized AI/developer CLI (separate machine/account)

The agent needs the private relay URL/repository name, a GitHub token scoped to it, and its own HMAC key. **This ChatGPT conversation does not magically gain those credentials or a persistent device socket.** If the authorized GitHub connector can reach the private relay, an AI can also create signed command issues and inspect response comments through that connector; the signatures must be computed in a trusted environment.

```sh
# In the authorized developer environment, secrets provided by its credential manager:
export V13_RELAY_TOKEN=... ; export V13_AGENT_KEY=...
python -m v13.remote_maintenance_bridge send --repo YOUR_ACCOUNT/YOUR_PRIVATE_RELAY --agent agent-core --command HEALTH
python -m v13.remote_maintenance_bridge send --repo YOUR_ACCOUNT/YOUR_PRIVATE_RELAY --agent agent-core --command LEARNING_STATUS
# The send result prints a PRIVATE GitHub issue link, e.g. https://github.com/OWNER/PRIVATE/issues/123
python -m v13.remote_maintenance_bridge read --repo YOUR_ACCOUNT/YOUR_PRIVATE_RELAY --issue 123
```

The `send` command creates a private GitHub Issue carrying the HMAC-authenticated bounded command (no passwords). The phone polls, validates the GitHub author + agent key + expiry + allowed operation, durably journals the request, posts a sanitized receipt as a comment, then closes the issue. A restarted poller never re-runs an interrupted apply. An invalid request receives **no diagnostic reply**. The agent can open the private link and read the result after a poll.

### Publish a signed online source patch

Create a real reviewed code change in the **developer repository** and push it to a commit `TARGET_SHA` (which contains the desired file). The previous currently installed source commit is `BASE_SHA`. The developer alone keeps its Ed25519 raw 32-byte signing key in a chmod-600 private file. Generate it locally with `python -m v13.remote_maintenance_bridge keygen --out /PRIVATE/PATH/agent-core-ed25519.raw` (prints **only** the public key, refuses overwrites). Add its corresponding *public* 32-byte key (base64) and allowed prefix to the Android trust file, using the existing `termux_patch_staging` format.

```sh
python -m v13.remote_maintenance_bridge publish \
  --repo YOUR_ACCOUNT/YOUR_PRIVATE_RELAY \
  --agent agent-core \
  --base-commit BASE_SHA \
  --target-commit TARGET_SHA \
  --path v13/code/v13/TARGET_MODULE.py \
  --signing-key-file /PRIVATE/PATH/agent-core-ed25519.raw
# prints patch_id and patch_commit (private relay commit)
python -m v13.remote_maintenance_bridge send \
  --repo YOUR_ACCOUNT/YOUR_PRIVATE_RELAY --agent agent-core \
  --command PATCH_STAGE --patch-id PATCH_ID --patch-commit PRIVATE_RELAY_COMMIT
```

For `PATCH_APPLY`, the user must enable `remote_apply_enabled=true`, grant the agent `PATCH_APPLY` in private config, and add the **exact intended file path** to `apply_paths`. That allows authenticated approved agents to modify that source file in future with no extra confirmation: treat this authority as powerful. **Never allow** the bridge itself, signature verifier, private config, public keyring or permission mechanism into auto-apply. Source updates are backed up. For a local, checksum-guarded source restore use `python -m v13.remote_maintenance_bridge rollback --config "$HOME/.v13-private/remote.json" --request-id REQUEST_ID`. The rollback does not restart V13; model/runtime restart and automatic native recovery are not orchestrated. If the user wants request-by-request approval, leave apply disabled and use staging only.

## Runtime diagnosis status contract

Optional local JSON `status_file` fields: `learning_mode`, `runtime_mode`, `last_error_code`, `world_status` (short symbolic strings), `queue_depth`, `world_steps`, `c3_steps`, `body_b1_steps`, `body_b2_steps` (nonnegative integers) and `organ_status` dictionary restricted to `B1`, `B2`, `C2`, `C3`, `WORLD`, `JEF`, `A5`. Values beyond this allowlist, including private prompts, user message text, paths, tokens and raw exception traces, are discarded. Until a real V13 runtime exporter populates this file, no learned weights or inference integration is claimed.

## Threat model, limits and tests

- No public port or shell. Requests authenticated by private GitHub access, *specific* GitHub author, separate per-agent HMAC key (not query-string password), and fixed command schema/10-minute freshness. Keys can be revoked locally.
- Private relay **must be private**; public source repository never receives user diagnostics. GitHub infrastructure still processes the redacted reports and command metadata; this is not end-to-end private from GitHub.
- The patch must be pinned to the private relay SHA, signed Ed25519, match the installed file preimage and agree byte-for-byte with a trusted developer repo target commit. A signed commit can still contain malicious code: human or automated code review remains necessary.
- Crash-safe SQLite journal prevents rerunning previously accepted requests, including uncertain interrupted applies. A crash between comment post and local posted-mark may cause an extra **duplicate comment**, not a repeated patch.
- Same Termux UID can alter its own files/config. **This is not an independent Android security boundary** and does not protect from arbitrary code already running with that UID. Do not grant this daemon root or Android Accessibility/ScreenCapture permissions.
- Current `PATCH_APPLY` only applies one existing Python source file, keeps original backup, supports checksum-guarded **local manual rollback**, leaves process restart manual, and does not promise cross-file atomic updates, model reload, or automatic rollback.
- Native Redmi/Android 13 networking, storage, low-memory constraints, GitHub rate limits and on-device authorization still require real-device verification. The software-only tests do not constitute live-device proof.

Related: #1756 signed patch staging, #1793 product requirement. This branch should be reviewed separately and merged after QA; do not silently promote Age-0 learning or other gates.