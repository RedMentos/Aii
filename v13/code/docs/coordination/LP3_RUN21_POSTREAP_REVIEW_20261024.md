# V13 LP3 Run21 — post-reap numeric PGID ownership review (2026-10-24)

## Exact base and scope

Base: PR #56 head `d534c35f10a163de810cfe9443d3fee56653968a`, stacked on Claude PR #38 `cb959052433e01c29afc007e02b93aef373deb7f`. Run20 launcher blob `7ef49985456294fd93da7671d8fbae8b26eeb20a`. Remote branches/open PRs checked before editing; no newer Claude integration PR seen. Canon, ROADMAP, production runtime, original LP3 preregistration, model, seeds, STEP2/B3 and all other owner files unchanged. This is a **code-only OFF-by-default review candidate**, not installed in production. Owner: LP3 launcher patch and Run21 scoped tests/evidence only. No parallel heavy jobs or other agent-owned edits.

## Reproduced problem and fix

Run20 `_cleanup_owned_group(pgid)` is invoked **after** `Popen.wait()` reaps the leader, but still calls `killpg(pgid, SIGTERM/SIGKILL)`. Once the original process group has fully disappeared, its numeric PGID may be reused; the old numeric value is no longer an exclusive ownership handle. In the Run21 adversarial mock the original code called `killpg(424242, SIGTERM)` and `killpg(424242, SIGKILL)` despite the leader already being reaped. This is a potential wrong-target signal, not a demonstrated real-world PID-reuse incident.

The isolated patch changes the post-reap helper into a **non-signaling probe**. If any group is observed, the attempt fails closed and poisons the local lock; cleanup is delegated exclusively to the freshly owned cgroup-v2 subtree. While the leader is still alive and unreaped, the existing bounded timeout/interruption group termination is unchanged. No new kernel privileges, no expanded native execution rights, no changed LP3 protocol.

## Evidence and limitations

- RED: `run21-red.log`, 2 tests with 1 reproduced failure, `killpg` called twice on a post-reap numeric PGID.
- GREEN: `run21-green.log`, 2/2 PASS after fix.
- Additional integration regression: first `run21-targeted3.log` failed because test incorrectly expected an unpoisoned lock; correct behavior is fail-closed poisoned lock. Preserved, test corrected.
- Assembled available LP3-focused suite: **148/148 PASS**, `run21-focused-final.log`. This subset was reconstructed from Run14/Run15/Run20 uploaded source packages; it is **not** the complete Run20 186-test collection or the full repository suite. `compileall` PASS.
- Current host: 4 GiB cgroup memory cap; `/sys/fs/cgroup` mount is read-only; no delegated LP3 parent; pinned seven HF assets and two fixtures absent; `transformers` absent. Read-only native readiness BLOCKED. No real cgroup `setsid()` negative control, native HF inference, Redmi or independent global ownership proof.
- Complete Git checkout, official full suite and official privacy scanner NOT RUN because container cannot resolve github.com; GitHub connector used to read current authoritative source metadata/docs and publish isolated checkpoint.
- No AGI/full-system claim; STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, full scope false.

## Primary technical references (checked 2026-10-24)

- Linux kernel cgroup-v2 docs: https://docs.kernel.org/admin-guide/cgroup-v2.html (cgroup.kill recursive owned subtree, process migration caveats).
- Linux process-group API: https://man7.org/linux/man-pages/man2/setpgid.2.html (group lifetime, group IDs and session semantics).
- Python subprocess: https://docs.python.org/3/library/subprocess.html (wait/reap, start_new_session, timeout cleanup).

## Exact next step

Independent full-checkout review, official complete tests/privacy scan, and writable delegated Linux cgroup-v2 **synthetic** setsid descendant and crash/stale-slot tests. Verify global job owner, pinned assets and RAM fit before any registered native four-seed cohort. After cohort, externally anchor closed raw receipt; separately run equal-budget generated-answer ablation. Keep every original gate unchanged. Rejected anyone-writable Drive backup destination must not be retried.
