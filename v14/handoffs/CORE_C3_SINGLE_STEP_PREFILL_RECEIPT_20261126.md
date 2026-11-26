# Core & Harness handoff — C3 single-step prefill receipt (2026-11-26)

## Ownership and ancestry

- Owner: Core & Harness
- PR: #2533 — Core: preserve C3 first-step prefill timing on early return
- Branch: core/v14-native-prefill-single-step-timing-20261126-run1
- Parent PR: #2532 — native prefill count audit
- Parent head: eae91af6d724b8d12530ed0b013afc7f5fed4372
- Latest code head at this handoff: 1677c3c58b4505ec40831c11151829e0e6fe46bc
- State: DRAFT / NOT_RELEASED / REDMI_UNVERIFIED

## Defect

The C3 first-token-bias native path returns early when max_tokens is one, no first token is produced, or the native first step stops at EOS/word. Before this change, the branch stored the native first-step timing at the top-level metrics object but omitted it from output_adapter_native_first_step.timings. The #2532 audit correctly uses the nested prompt-bearing first-step record as the authoritative timing source. Consequently, a valid one-step completion could be reported as lacking prefill timing.

## Implementation

1. Preserve first_step.timings inside output_adapter_native_first_step on every early return.
2. Add a loopback HTTP test that drives the real LlamaRunner.generate() first-token-bias path with max_tokens=1 and an EOS response.
3. Assert both B1_DETAIL and B2_GIST offers are represented in the native offer receipt and the native prompt token count matches prompt_n + cache_n (24 = 20 + 4).
4. Assert the report remains metadata-only and does not expose the test's private quote/user sentinel values.

## Strict source-chain repair

Exact-head staged workflows initially exposed nested immutable pins after the runners.py change. They were rebound bottom-up without weakening any allowlist:
- native receiver BASE_PINS → exact runners.py SHA-256 a7f0f67c55ebc6c3fe61f223d1c4bf7f853c5c41293b3a4cc802646a7f386096;
- recovery-21 builder → exact native receiver Git blob 48e4a73c89580789b1574459f892998fa9967035;
- stage_integrated_candidate.BUILDER_SHA → exact recovery-21 SHA-256 6e9d657bc8a1dc9de8213f1ef744bc5c01f34eb801d03f448af9dd0040088512;
- RuntimeDeploy.STAGER_SHA256 → exact stage builder SHA-256 1e8e2e736ea681f068f1969057de7e05bcd99c986ab43e6f875a3ea8a496172d.

## Exact-head test evidence

At head 1677c3c58b4505ec40831c11151829e0e6fe46bc:
- PASS — phone offer receipt evidence, run 45838222712.
- PASS — coordinated source contracts, run 45838222782.
- PASS — runtime deployment integrity, run 45838222659.
- PASS — private owner-read Termux bootstrap, run 45838222791.
- PASS — Core native stream integrity, run 45838222717.
- PASS — fastpath and interrupted-runner warm retention, run 45838222676.
- PASS — Lab Age / WebView truth, run 45838222757.
- PASS — two-checkout updater migration, run 45838222669.
- IN_PROGRESS at last readback — staged context and integrated regression, run 45838222818. This must be checked again before review; no green claim yet.

LOCAL_LINUX full repository checkout/pytest: BLOCKED / NOT_RUN because git ls-remote https://github.com/RedMentos/Aii.git fails DNS resolution and no Aii checkout is mounted. GitHub CI is not local execution.

TERMUX/REDMI: REDMI_UNVERIFIED. No connected handset receipt, APK install, native GGUF run, MediaProjection consent, update request or device action. No model/weight/permission/data change.

## Product meaning and limits

This closes a real telemetry gap in the C3 first-token-bias path and preserves the native prompt-bearing prefill timing needed by the existing B1/B2 offer audit. It does not prove semantic use of B1/B2 content, correct answer quality, trained latent coupling, native Redmi execution, or whole-system completion.

## Next action

1. Re-read exact run 45838222818 for the latest head. If green, request independent Boss/QA review of #2533 and its parent #2532; do not merge a child without its parent.
2. Continue the actual B1/B2 → C4 → C3 correctness/quality path; token-count parity is not semantic-consumption proof.
3. Rebase/compose MediaProjection provider #2379, registry/recovery #2406 and Perception RAW EYE ingress #2375 on the current #2513/#2528 Android action stack. Keep screen_capture OFF until the combined provider/registry/transport/lease/Perception consumer passes exact CI.
4. No user action required. Production B3 remains OFF.
