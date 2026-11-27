# V14 live project index

This folder is the active V14 development record for the complete V13 / Inquisition-JEPA product. V14 reorganizes and extends the architecture; it does **not** remove historical V13 functions.

## Read before each development run

1. [Full V14 master and unchanged historical V13 Canon](V14_MASTER_BLUEPRINT_AND_RESEARCH_20261119.md)
2. [Executable live workplan](V14_LIVE_WORKPLAN.md)
3. [Team ownership and operating system](V14_TEAM_OPERATING_SYSTEM.md)
4. [Machine-readable work board](V14_WORK_BOARD.json)
5. [Next user action and verified device boundary](V14_USER_NEXT_ACTION.md)
6. [Research and OSS/license ledger](V14_RESEARCH_LEDGER.md)
7. [Whole-Canon coverage index](V14_CANON_COVERAGE_INDEX.md)
8. Root [AGENTS.md](../AGENTS.md) and the active code-area AGENTS files.

## Source-of-truth rules

- The master contains the current architecture and the complete historical V13 Canon in Part III. Do not silently shorten, replace or reinterpret an obligation.
- Workplan, research ledger, board and next-action file are live operational records; update them only with verified facts and preserve older evidence as dated history.
- Before a material master change, create and read back an immutable backup under `backups/`. Do not rewrite the historical Part III source bytes.
- Use the newest verified release-development HEAD and inspect open PRs, branch owners, CI and handoffs before editing. The old branch name is a continuity hint, not a permanent pin.
- Keep agent ownership disjoint, use reviewable branches, never force-push, and do not call a draft PR integrated functionality.

## Evidence vocabulary

`SPECIFIED`, `CODE_PRESENT`, `CONNECTED`, `WIRED_SYNTHETIC`, `LOCAL_LINUX`, `NATIVE_LINUX`, `ANDROID_ARM64_CROSS_COMPILE`, `REDMI_NATIVE`, `WEIGHTS_UPDATED`, `HELDOUT_UTILITY_PASS`, `RELEASED` are distinct. A Linux build or synthetic Runtime test is not a Redmi test. A native input-embedding probe is not a trained latent channel. A GitHub merge is not an installed-device update.

## Core product constraints

- Preserve the distributed A/B/C, latent, World/Self/Memory, JEPA, Sleep/Replay, voice, tool and Android-control end goals.
- Keep fastpaths for obvious requests while allowing deeper organ collaboration for nontrivial requests.
- Keep official Age separate from lab test rights and compute/resource limits.
- External Android effects require OS-granted capabilities, explicit user consent, audit, cancel/stop and rollback where possible.
- Never change installed models, weights, permissions or user data without the required explicit approval.
