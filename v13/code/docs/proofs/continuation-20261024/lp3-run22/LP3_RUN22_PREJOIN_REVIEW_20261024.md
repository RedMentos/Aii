# V13 LP3 Run22 — Python pre-join bootstrap isolation (2026-10-24)

## Verified base and file ownership
- Base: PR #57 head `0d72d55f25fabd71465ee3d6196fdeb9815a5277`, descendant of Claude PR #38 `cb959052433e01c29afc007e02b93aef373deb7f`.
- Remote branches, open PRs, AGENTS, handoff, BUILD_STATE, ROADMAP, user decisions, and full Canon checked before edits. No newer open Claude integration PR found.
- Single owner: isolated `lp3_cgroup_v2.py` patch + Run22 tests/evidence/docs. Other owners, frozen runtime, original model, registration, seeds and gates untouched. No heavy native jobs started.
- This is a source candidate **not installed** in the production `v13/code/scripts` checkout. Local assembled test workspace only.

## Reproduced defect
`CgroupV2Job.wrap()` in Run21 invoked `sys.executable` with `lp3_cgroup_join.py` directly. CPython may execute `site`, executable `.pth` lines and site hooks **before** executing the helper script. Such startup code can spawn processes before the helper writes its own PID into the delegated cgroup, undermining the stated pre-fork containment premise. This is a real pre-join Python-code-execution counterexample in a private venv; it is **not** a demonstrated detached native child or kernel containment escape.

The strengthened RED test creates a private virtualenv with an executable `.pth` that writes a sentinel before the helper reaches the fake `cgroup.procs` path. The ordinary interpreter control proves the injection is active. The Run21 command executes the hook and fails both tests (`run22-red-v2.log`). An earlier attempt using `PYTHONPATH/sitecustomize.py` gave one false pass because this host's existing sitecustomize masked it; this false-start is preserved in `run22-red.log`.

## Fix and independent cross-check
Use `[sys.executable, '-I', '-S', helper, ...]` **only** for the stdlib-only pre-join helper. `-I` ignores PYTHON* environment and unsafe import paths; `-S` disables site processing. The unchanged registered runner is `execv`'d after membership check. Test confirms that the hook does not run, that the helper actually reaches the missing `cgroup.procs` (not merely failing to import), and that the wrapper command preserves all arguments. `run22-crossreview.log`: 2/2 PASS; focused available LP3 tests: 150/150 PASS, `compileall` PASS. No actual writable-cgroup kernel proof.

## Evidence level and limitations
- Software/LINUX synthetic: real Python interpreter startup injection with temporary venv and fake cgroup path; **not** a real cgroup join.
- Current host: 4 GiB memory.max, read-only cgroup2 mount, no delegated parent. Registered seven HF files, two fixtures and transformers absent. Native readiness BLOCKED; no LP3 native inference, no Redmi measurements.
- No full Git checkout due container DNS; full repo suite and official privacy scanner NOT RUN. The focused 150 tests do not supersede Run20's historical 186 or the full suite.
- `STEP2=UTILITY_FAIL`, `B3 L1=FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, canonical and user scope incomplete. No AGI claim, no gates relaxed.
- Rejected anyone-writable Drive backup destination not retried.

## Primary references accessed 2026-10-24
- CPython command-line options: https://docs.python.org/3/using/cmdline.html (isolated `-I`, disable site `-S`).
- Linux kernel cgroup v2: https://docs.kernel.org/admin-guide/cgroup-v2.html (fork inheritance; process migration; recursive populated/kill).
- Python subprocess: https://docs.python.org/3/library/subprocess.html (`Popen`, `start_new_session`).

## Exact next step
Independently apply the hash-bound patch on a complete current checkout; run full suite and official privacy scanner. Then on a writable delegated Linux cgroup-v2 host run the real synthetic detached-`setsid()` and crash/stale-slot containment proof. Independently verify global job owner, pinned native assets and measured RAM fit before any unchanged registered LP3 four-seed native cohort. Externally anchor closed evidence; separately measure generated-answer utility.
