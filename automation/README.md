# V13 reviewed release queue

The default-branch GitHub Actions workflow `.github/workflows/v13-reviewed-release-queue.yml` runs twice per hour and can be triggered manually. It is independent of the five hourly ChatGPT coding agents. **It does not pick features or interpret private diagnostics.**

## Who does what

The four specialist agents implement and test on independent PR branches. **Boss & Integration** reviews actual code differences, reproductions, dependencies, safety boundaries and relevant green CI before nominating compatible, runnable changes. The phone's fixed source channel is `gpt6/v13-private-remote-bridge-20261111`; Android only gets code after release-branch exact-commit CI plus the existing local CI-gated update/deploy path.

For a **low-authority candidate only**, Boss must:
1. Bring the PR onto current phone-release ancestry: PR base exactly `gpt6/v13-private-remote-bridge-20261111`, head on `RedMentos/Aii`, not draft and mergeable. Fix stacked dependencies and conflicts first.
2. Require successful, exact-head GitHub Actions for `V13 staged context and integrated regression` plus `v13-private-remote-bridge-tests`. For phone-related paths also require `V13 private owner-read Termux bootstrap`. Failed, missing or stale checks block.
3. Review path scope and side effects, a focused reproduction, real test results and a rollback path. On the PR post a **standalone line** as the repository owner exactly:
   `V13-RELEASE-APPROVED SHA=<the complete 40-character current PR head SHA>`
   Include a concise factual test rationale below it. Then add the `v13-release-ready` label. A subsequent commit requires a new SHA approval, even if the label remains.
4. The queue checks SHA/owner/ancestry/changed paths/CI/mergeability again and merges **at most one** safe PR per run. The resulting release commit must pass its own **push** CI before the phone updater can activate it.

The runner creates its candidate label on its first scheduled/manual execution. It never merges without both a labeled PR and a SHA-bound owner comment.

## Not eligible for unattended merge

The automation refuses workflow files, Canon/model metadata and critical phone updater/permission/runtime files, binary weights, deleted/renamed files, untrusted forks, large change sets and stale/diverged PR ancestry. These require direct Boss review, integration with regression tests and exact-release-push CI instead; they are not forbidden from development.

Never promote an AGI/JEPA weight-learning experiment, model replacement, new OS capability, network permission or remote shell simply because an automated merge succeeded. Keep the existing local device permission controls, rollback and failure gates. The queue does not poll the private relay, export user data, read Termux files or command Android.

## Evidence-driven continuous development

Each hourly agent may inspect **authorized** `RedMentos/Aiiii` owner-relay diagnostics and user-submitted private `V13PHONE` reports; only fetch bounded chat log pages after the user's separate on-device log-sharing opt-in. Summarize private evidence into technical causes and counters without copying raw contents, identifiers or credentials into public GitHub. Distinguish `CI_GREEN`, `RELEASE_MERGED`, `PHONE_UPDATED`, `RUNTIME_RESTARTED` and `NATIVE_UTILITY_VERIFIED`: they are not interchangeable.

The goal is a measured loop — real issue -> baseline -> patch -> regression -> review -> release -> Redmi verification -> next improvement — rather than increasing a count of open PRs.
