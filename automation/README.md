# V13 continuously reviewed phone release queue

The default-branch workflow `.github/workflows/v13-reviewed-release-queue.yml` runs twice per hour. Five hourly specialist agents create code; this queue now evaluates their PRs rather than staying silent when no manual label was set.

## Two independent release lanes

**Strictly additive research modules:** owner-authored PRs from `RedMentos/Aii` targeting the fixed phone branch may be automatically selected even if marked Draft or based on an older release commit, *only* when all affected files are newly added inert modules under `v13/code/v13/`, matching new `test_*.py` files, or documentation in `v13/code/docs/handoffs/`. At most 8 modules, 12 test files, 20 files total and 650 changed lines. No modified runtime modules, installer, permission system, CI, model specs, model weights, tools, network capability, deletion, rename or content from a fork is admitted. Actual GitHub mergeability and exact PR head remain mandatory.

The read-only GitHub workflow `V13 safe additive candidate tests` compiles all new modules and actually **runs the newly supplied tests** on the exact candidate head. The separate existing `V13 staged context and integrated regression` and `v13-private-remote-bridge-tests` must also be green at that head. No arbitrary PR content is used as integration instructions. A candidate without its test run stays in the queue.

**Existing executable runtime, permission or update code:** requires deliberate Boss review, focused tests, manual release integration and exact phone CI. The user wants automatic integration, not hidden removal of critical safety guarantees. A labelled PR with an owner-authored standalone `V13-RELEASE-APPROVED SHA=<exact 40-hex head>` and green CI can still enter the older reviewed queue, but the scheduler never grants rights to itself.

## GitHub merge → exact release CI → Redmi

GitHub's own `GITHUB_TOKEN` merge may not fire normal push workflows. The queue therefore launches `workflow_dispatch` for the three trusted release checks against the fixed release branch after every merge. All three workflow files are registered on default branch, and the release branch contains the executable versions. The queue verifies the merge SHA is the current release head before dispatching. Subsequent hourly checks repair **missing** CI runs; an actual failed test is never falsely green or retried blindly. At most **one** PR is merged per queue run so remaining candidates see the updated release head.

The phone update agent continues to check exact-commit, successful CI on the release SHA and then deploys the immutable runtime source through `runtime_deploy.py` and refreshes the dashboard. Device opt-in, maintenance locks, process lifecycle, user stop state and rollback are independent: this GitHub workflow cannot toggle them. `UP_TO_DATE` means installed release matches the release branch, *not* that all open development PRs are integrated.

## Evidence and ownership

Treat status as five different facts: `CODE_WRITTEN`, `PR_CI_GREEN`, `RELEASE_MERGED`, `PHONE_UPDATED`, `NATIVE_UTILITY_VERIFIED`. The first does not imply any later state. Each agent should inspect relevant authorized private technical diagnostics when available, publish tests and a release-compatible PR, and help resolve its own blocked CI. Boss checks runtime code and integrates compatible changes. Never publish private chat, device logs, GGUF weights, or credentials in public issues or CI output.

This automation alone does not implement internal B1/B2 conversation, on-device JEPA training, learned sparse experts or age promotion. Those use separate scheduler/runtime implementations and require real Redmi tests.

The workflow registrations on default `main` are restricted to the phone-release PR base and dispatch events. They must not run phone tests against this automation-only branch, which does not contain the full V13 runtime sources.
