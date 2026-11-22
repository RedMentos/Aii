# Core handoff — native-probe operator dispatch

Date: 2026-11-22  
Role: Core & Harness  
Branch: \`core/v14-native-probe-operator-dispatch-20261122\`  
PR: [#2381](https://github.com/RedMentos/Aii/pull/2381)  
Exact branch head at handoff: \`1252e4e7ee5cd194b6cb9d46a208c3bd3e1bbb19\`  
Base: QA branch \`qa/v14-native-probe-model-hash-20261122\`, base SHA \`42723cfd4c0629940b75c158283bdf5256568142\`

## Concrete defect

QA PR #2377 originally added the source/model-bound approval tests but the public operator consumer was missing. At its earlier exact head \`fcb7e8c2b70e675c46741d919626ad4fd34ceb38\`, workflow run #45066958323 showed 11 failures / 14 passes in both Python 3.13 and 3.14. Ten failures were rejected \`:callosum arm-probe\` / \`:callosum native-probe\` commands; the deadline test also found that \`v13.callosum.time\` was not imported. The pinned Linux receiver build and Android arm64 cross-compile jobs succeeded on that older head.

The QA branch then advanced to \`42723cfd4c0629940b75c158283bdf5256568142\` and changed its native-receiver workflow to run the approval tests only with the staged operator overlay. Its exact-head workflows #45071147374 and #45071147387 were queued when checked.

## Implemented in this branch

- \`:callosum arm-probe SENDER RECEIVER --last-source --confirm\` creates the existing 120-second one-shot local approval.
- \`:callosum native-probe SENDER RECEIVER --last-source --confirm\` requires that exact approval, the latest FINAL source, unchanged model revisions/hashes, and an installed staged \`cognition.native_receive\` consumer. If the staged consumer is absent, it fails before consuming the approval.
- \`:callosum revoke-probe\` revokes a pending approval.
- A separate local Store route-binding record is keyed to the full approval nonce. It compares canonical \`ModelManager.path_for(role)\` and manifest paths both before arming and during consume. It does not hash large GGUF files a second time; the approval module remains responsible for byte/hash verification.
- Probe deadline is hard-capped at 120 seconds using monotonic time. After a consumed attempt, route state is cleared and the native pool is synchronously unloaded.
- Results claiming production routing, semantic-use proof, or nonzero training/native-receiver authority are rejected. This remains a diagnostic input-effect probe, not learned B3.

Files changed:
- \`v13/code/v13/callosum.py\`
- \`v13/code/tests/test_native_latent_receiver_operator.py\`
- \`.github/workflows/v14-core-native-probe-operator.yml\`

## Evidence

| Environment | Exact test | Result |
|---|---|---|
| LOCAL_LINUX, Python 3.13.5 | Isolated route-binding harness: exact manifest path, byte-identical alternate-path rejection, symlink rejection; \`py_compile\` | PASS |
| LOCAL_LINUX, full Aii checkout | Full Runtime/Operator suite | BLOCKED — no Aii checkout is present in this execution container |
| CI | New workflow run #45071358963 | QUEUED at handoff |
| CI | Existing staged/integrated workflow #45071359009 | QUEUED at handoff |
| TERMUX/REDMI | Installed candidate, native probe, model process and actual B3 effect | REDMI_UNVERIFIED; no device action performed |

The local helper harness is not a full repository test and is not described as one. The branch's exact CI must pass before this work is considered verified.

## Safety and integration limits

- No model download, model swap, weight edit, native probe, Android permission change, or device mutation was performed.
- B3 remains OFF. No production routing, semantic use, learning authority, or trained latent transfer is claimed.
- The actual \`native_receive\` method is part of the staged recovery→stage→deployer candidate. This operator path refuses to run until that consumer is present.
- The native loader still opens a filesystem path rather than a verified file descriptor. The path-identity and byte checks narrow the risk but do not remove a privileged/concurrent-writer TOCTOU window; an immutable private copy or verified-FD loader is the stronger follow-up.
- The current release/device proof is not refreshed by this PR. Latest Boss handoff reports no authenticated private owner-read reply; installed SHA and updater consent are UNKNOWN. REDMI_UNVERIFIED.

## Next exact action

1. Wait for #2381's Python 3.13/3.14 approval, route-binding, staged Runtime and privacy workflows.
2. If green, request independent QA review of the path-binding sidecar and merge this stacked fix into QA #2377; do not merge to release directly.
3. Boss then composes the approved native receiver, local approval and operator consumer through the shared recovery→stage→deployer/source-pin chain.
4. Only after the exact integrated candidate is built and reviewed should a separate explicit user decision be requested for one diagnostic probe. A ChatGPT message alone does not operate the disconnected Redmi.
