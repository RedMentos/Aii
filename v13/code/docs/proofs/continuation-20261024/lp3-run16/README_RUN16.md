# V13 LP3 Run16 — serial cohort launcher checkpoint (2026-10-24)

Base: PR #51 `b6d1cbaf43f9099a902cd252ae9af133497f6610`, which descends from Claude PR #38 `cb959052433e01c29afc007e02b93aef373deb7f`. No newer Claude integration PR was open at the start of this run. Canon `V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` and production runtime unchanged.

**Status: isolated tested SOURCE CANDIDATE; not installed into production or executed against a native model.** Source and tests are preserved in `SOURCE_AND_TESTS.tar.xz` (Git blob `667d7f1b73a655097a44ff4c61749af113f7544f`, SHA-256 `041e0014194ffdfd74aef79cf6a9149e6c2e11ad51b859bc9a9e7e81b1b67516`). Full docs, closed synthetic raw logs, direct native preflight, SHA256SUMS and BUILD_STATE are preserved in `RUN16_PROOFS.tar.xz` (Git blob `640bfdae2630b4861e0ababd00ccdbaa01bff494`, SHA-256 `9f14ca4cab695d4617a3d6ced79f0468121684fcdbb2e6835f982925a11ffe41`).

Unpack both archives from a verified current checkout root **only after checking path ownership and absence of newer files**:
```sh
tar -tJf SOURCE_AND_TESTS.tar.xz
tar -tJf RUN16_PROOFS.tar.xz
tar --keep-old-files -xJf SOURCE_AND_TESTS.tar.xz
tar --keep-old-files -xJf RUN16_PROOFS.tar.xz
cd v13/code
python -m unittest discover -s tests -p 'test_lp3_*.py' -v
python -m compileall -q scripts/lp3_serial_cohort.py tests/test_lp3_serial_cohort.py
```
The launcher is read-only by default; `--run` additionally requires externally checked global job ownership and actual RAM fit, local nonblocking flock, exact preregistered model/source readiness, and fresh evidence paths. It launches the original four-seed runner once, preserves failed attempts, audits before closing and writes a local external receipt. A local receipt is **not** an independently published anchor. No new library, organ, gate or experiment parameters.

**Tests:** 102/102 LP3-focused software/synthetic PASS (89 inherited, 13 new); compileall PASS. No full repository checkout/full-suite or official branch privacy scan due to GitHub DNS failure in test container. Local preflight BLOCKED: cgroup 4 GiB, seven HF assets missing, LP2/LoRA fixtures absent in partial bundle, `transformers` absent. No native LP3 or Redmi run.

**Unchanged:** STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; full architecture incomplete. No user decision needed. The rejected anyone-writable Drive backup was not retried.

**Next:** integrate source files in a complete current checkout after independent review; full suite and official privacy scan; verify global native job ownership, model/fixture bytes and RAM fit; serial four-seed run; publish externally anchored receipt; separately preregister equal-budget generated-answer ablation.

Research/provenance (2026-10-24): Python `fcntl` https://docs.python.org/3/library/fcntl.html; Python `subprocess` https://docs.python.org/3/library/subprocess.html; Linux `flock(2)` https://manpages.debian.org/testing/manpages-dev/flock.2.en.html; cgroup v2 https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html. New package uses Python stdlib only, no third-party code copied.
