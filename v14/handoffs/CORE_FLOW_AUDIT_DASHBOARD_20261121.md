# Core flow-audit dashboard handoff — 2026-11-21

## Current-base consolidation

- Release branch: `gpt6/v13-private-remote-bridge-20261111`
- Rebased on verified release ancestor `e18c664d954fa5a44a1b2e5bec76850d5a40f89f`; no force-push.
- Consolidates the read-only auditor from #2183 with the local dashboard consumer from #2188. #2183 can be closed as superseded only after this PR's exact-head checks are green.
- The dashboard intentionally selects the **latest completed assistant turn across all chats**, not necessarily the currently open chat. The UI now says so explicitly. The audit is then constrained to that event's actual session before reading packets and source refs.

## User-visible behavior

The local WebView adds an explicit **Organdurchlauf prüfen** action and token-scoped, read-only `GET /flow-audit` endpoint. It reports bounded A5/B1/B2/C4/C3/C5/B3 counts, model labels, native-token receipt source, prompt/output tokens, TTFT/duration, source-integrity counts and warning codes. It returns no event/session IDs, source IDs/hashes, prompt/chat text, body summaries, token IDs, raw audio or source bytes. Rendering uses `textContent`.

The selector uses the same hardened Store reader as the auditor (AndroidControl path policy, read-only SQLite, `O_NOFOLLOW`, owner/link/inode checks). A newer pending turn with no assistant answer does not displace the latest completed turn. The standalone CLI remains session-explicit.

## Checkpoint

- Current consolidated commit: `f4b53332554c240efc632e9b98419376d707cfde` (merge commit with parents `4517c81051b93bfb656961c18d84c3ec01e22652` and release base `e18c664d954fa5a44a1b2e5bec76850d5a40f89f`). The branch was advanced without force-push and the changed-file tree was read back from GitHub.

## Verification boundary

- Dedicated workflow: pending on the new exact head.
- Existing full staged/integrated workflows: must be checked on the exact head; CI is Linux evidence, not a Redmi test.
- Local exact Aii checkout: BLOCKED by the observed GitHub DNS failure in this environment; no local full-repository PASS is claimed.
- Fixtures are synthetic. Runtime-reported model/token metrics are not device-attested. C3 source-bound context does not prove semantic attention. B3 tap/symbolic counts do not prove native latent injection.
- Deployment: NOT_RELEASED. No updater or phone action was triggered. Redmi remains REDMI_UNVERIFIED.

## Next owner action

Boss/Integrator reviews the existing dashboard handler/template path because the safe-additive gate correctly treats those existing UI files as higher-authority than inert additive modules. After review and green exact-head CI, integrate through the normal pinned runtime/dashboard update path. A fresh private owner-read receipt is still required before claiming installation or user-device effect.
