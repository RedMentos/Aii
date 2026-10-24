# V13 Run25 — independent review of Run24 atomic clone3 staging

Base PR60 `aba022002f445180dab355921626f8459e87e2a9`. Isolated review only, OFF by default. No production runtime, Canon, original LP3 preregistration, seeds/model or negative gates modified.

## Reproduced and fixed
- C used `realpath(path, canonical)` with a 2048-byte stack buffer, smaller than PATH_MAX on common Linux systems. Fixed via `realpath(path,NULL)`, allocation cleanup and path-size bound. Standalone Linux AddressSanitizer undersized-buffer control reproduced stack-buffer-overflow. This is a class-level reproduction, NOT a cgroup-path exploit demonstration.
- Python marker verifier silently accepted duplicate JSON keys. Added strict `object_pairs_hook` rejection.
- Marker verifier followed symlinks and accepted unbounded input. Added `O_NOFOLLOW`, regular-file check and 4096-byte cap.
- Rejected noncanonical cgroup path aliases, nonpositive helper PID and identical helper/child PID.

## Evidence
Before fix: 5/5 adversarial tests FAIL (reproduced); after fix: 7/7 new PASS + 11/11 inherited Run24 PASS = 18/18 software/Linux-negative-control PASS. C static compile and Python compileall PASS. The full raw RED, GREEN and ASAN logs are preserved in the separately hashed Run25 checkpoint archive. No positive `CLONE_INTO_CGROUP` kernel test, native LP3 or Redmi run. Full repo suite and official privacy scan remain NOT RUN because this container cannot clone the repository.

## Required gates
STEP2=UTILITY_FAIL; B3 L1=FAIL; Body-JEPA=UNAVAILABLE; jepa_weight=0; full architecture INCOMPLETE. The Run23 SIGTERM flake remains OPEN. No new feature is enabled.

## Remaining
Review the still-open parent-path TOCTOU risk (openat2 RESOLVE_NO_SYMLINKS) before production consideration. Obtain real delegated-cgroup synthetic proof before integrating the atomic helper. Meanwhile prioritize independent functional Canon packages instead of expanding only LP3 safety wrappers.

Sources checked 2026-10-24: https://man7.org/linux/man-pages/man2/openat2.2.html ; https://man7.org/linux/man-pages/man3/realpath.3.html ; https://docs.python.org/3/library/json.html .
