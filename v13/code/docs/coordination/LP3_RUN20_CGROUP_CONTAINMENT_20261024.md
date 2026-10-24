# V13 LP3 Run20 — kernel cgroup-v2 containment candidate (2026-10-24)

**Verified starting point:** PR #55 `01242b1e2c9c24f3345764bb57d06d096f34b239`, Run19 launcher Git blob `394deb439b1305534dcb3f51c916a0250f79c4c1`, stacked on Claude PR #38 `cb959052433e01c29afc007e02b93aef373deb7f`. Checked current open PRs, branches, `AGENTS.md`, `v13/code/docs/HANDOFF_CURRENT.md`, `v13/code/BUILD_STATE.json`, `v13/ROADMAP.md`, `v13/NUTZER_ENTSCHEIDUNGEN.md` and complete Canon v10.16.1. No newer Claude PR observed before edits. Only isolated LP3 candidate files and new scoped evidence; no production runtime, registered LP3 experiment, model, seed, Canon, Roadmap, or other owner's files modified.

## Confirmed defect / package

Run19 detached-session negative control: the leader spawns a descendant that calls `setsid()` and exits. The Run19 process-group-only wrapper published `LOCAL_CLOSED_EVIDENCE_UNPUBLISHED_ANCHOR` and a local receipt while the detached child lived. Original `run19_detached_red.log` is preserved in PR #55. **Run20 does not erase this failure or retroactively promote Run19.**

Run20 creates an isolated **OFF-by-default** cgroup-v2 candidate: `lp3_cgroup_v2.py` + `lp3_cgroup_join.py`, and changes the bundled `lp3_serial_cohort.py` to refuse all `--run` calls without an explicitly delegated cgroup-v2 parent. An exclusive `lp3-active` cgroup slot is created atomically; it persists across wrapper SIGKILL/crashes and prevents automatic relaunch until inspected. A minimal Python helper joins the fresh cgroup *before* executing the registered runner and writes a join marker after checking membership. The parent checks marker, `cgroup.events populated`, kills only its own cgroup subtree via `cgroup.kill` if residue exists, and **refuses any receipt even if the residue was killed successfully**. Unresolved cgroup cleanup poisons the host-local lock. The older process-group cleanup remains defense in depth. No unowned process is signaled.

**Important limits:** This is NOT a security sandbox against a privileged or intentionally migrating process; delegated parent permissions, kernel version, cgroup namespaces, actual `cgroup.kill` behavior and unexpected host restarts require a live kernel test. Same-parent exclusivity does NOT prove global ownership across hosts or other cgroup parents. Linux-only experimental launcher, not a requirement imposed on the Android production architecture. A real native four-seed cohort remains prohibited until full-checkout review and verified kernel containment, model assets, global owner, RAM fit and original gates. The candidate source is delivered in a source bundle, NOT installed into production.

## Software / synthetic evidence

- Initial new-test run: **36 tests, 1 FAIL and 1 ERROR**, caused by incorrect fake `cgroup.procs`/marker semantics in the test harness; raw `run20-first.log` preserved.
- Corrected targeted tests: 36/36 PASS, later 38/38 PASS after two more checks.
- First assembled focused run: 184 tests, 5 FAIL from inadvertently using an older Run13 auditor, 1 SIGTERM error from the container's command-time limit; raw `run20-focused-first.log` preserved. Restored the actual Run14 auditor before retest.
- Assembled follow-up: 184 tests, 1 inherited 2-second synthetic child timeout failure; raw `run20-focused-async.log` preserved. Increased only the **synthetic test harness** timeout to 5 seconds, not the native preregistered timeout.
- Full assembled LP3-focused software/synthetic suite: **186/186 PASS**, 38.518 seconds; raw `run20-final-current.log`. Includes inherited duplicate tests; not 186 unique new tests. `compileall` PASS.
- Native readiness on this host: **BLOCKED**, 4 GiB cgroup, read-only cgroup2 mount, no delegated LP3 parent, seven pinned HF snapshot files absent, LP2/LoRA fixture sources absent, `transformers` absent; source hash check only for registered candidate. No actual cgroup kill/setsid kernel experiment, HF inference, Redmi or global-owner proof.
- Complete repository suite and official privacy scanner **NOT RUN**: full Git checkout unavailable due github.com DNS. Manual narrow package inspection is not a substitute.

## Primary sources checked 2026-10-24

- Linux kernel cgroup v2 authoritative documentation: https://docs.kernel.org/admin-guide/cgroup-v2.html — fork inheritance, recursive `cgroup.events populated`, `cgroup.kill` kills entire subtree and coordinates concurrent forks; cgroup migration remains a caveat.
- Python subprocess documentation: https://docs.python.org/3/library/subprocess.html — `start_new_session`, process groups, `preexec_fn` unsafe in threaded programs; separate pre-exec helper used instead.
- Python signal documentation: https://docs.python.org/3/library/signal.html — SIGTERM handling is not SIGKILL protection.

## Ownership and next exact step

Owned: new isolated LP3 cgroup modules, launcher candidate patch, test adaptations/new tests, Run20 scoped docs/proofs only. Other agents retain production runtime, canonical files, STEP2/B3, phone and original preregistered LP3 runner. No heavy native jobs started. Next: independent review in complete current checkout, official full suite/privacy scan; on a **writable delegated Linux cgroup-v2 test host**, run a real synthetic detached-session descendant through this candidate and prove cgroup.events/kill/receipt behavior, crash recovery and cleanup. Only after that recheck pinned HF resources and independent global owner/RAM budget, run unchanged four-seed native LP3 cohort serially, publish independently anchored raw receipt and perform separate equal-budget generated-answer ablation.

**Gates unchanged:** STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; `canonical_architecture_complete=false`; `user_full_scope_complete=false`. No AGI/full completion claim. Rejected anyone-writable Drive backup not retried.
