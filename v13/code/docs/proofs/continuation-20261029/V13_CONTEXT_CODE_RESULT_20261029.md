# Context OS exact code-span source-preservation — verified software result (2026-10-29)

Owner: GPT-6; draft review PR #1084, exact parent PR #1083 `48a58ca8ca49c0b908509e04081cf9fc132017fd`. Binding Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## Original failures and source

- Prospective prereg `ce769b5abe626d04db2e9fbe6134a2e3d404e369` before tests and code. Original [RED run 40866038357](https://github.com/RedMentos/Aii/actions/runs/40866038357) reproduced **six** exact-code compression failures on 37 focused tests; original ZIP SHA256 `756145c2a0c646a5bab2eb16fce0b5d0ffb249fefbe0b5250f61861e71c7a09d`, CRC clean, 21/21 hashes. Private backup byte-equal at `/V13/RawEvidence/2026-10-29/V13_CONTEXT_RED_40866038357_sha756145c2.zip`.
- Initial fixed-source [run 40866180445](https://github.com/RedMentos/Aii/actions/runs/40866180445): 37/37 focused PASS but **FULL RED** (3089 tests, 4 torch import errors) due isolated workflow omitting torch, not a code test failure. Original ZIP SHA256 `b7ae9aec4cbe17182f92eb88d086053cd63dda71b0dc9745d41da7669204205b`, 21/21 hashes, private backup byte-verified. Dependency repair preregistered in `CONTEXT_OS_UNCLOSED_CODE_CI_DEP_ADDENDUM.md` and uses the already proven pinned V13 CPU torch/full-suite set.
- Source change: `v13/code/v13/context_os.py` Git blob `d28036f8ede96d031ec38a608c76549936c21eea`, test blob `a7271a41e6b8fec7c8aeffa3c174f4de18e86363`. Unclosed/ambiguous Markdown backtick spans keep RAW; valid closed inline/fenced spans still exact-pinned.

## GREEN

- Exact source-pinned [Actions 40866812715](https://github.com/RedMentos/Aii/actions/runs/40866812715), head `c80e855030b77c5b146918d5a3304ab368724039`, **SUCCESS**.
- **37/37 focused PASS; 3115 full software tests PASS, 11 skipped**. All nine stage exits SOURCE,VENV,DEPS,PIP_CHECK,FOCUSED,FULL,COMPILE,PRIVACY,DIFF = 0; privacy CLEAN; no native/model downloads.
- Original artifact `12893529245`, ZIP SHA256 `6884b2cdbd4495d9518eed8ae38d1b91408184da4fb8f497c04e4a334a4182f8`, CRC clean, 21/21 SHA256SUMS; privately backed up at `/V13/RawEvidence/2026-10-29/V13_CONTEXT_GREEN_40866812715_sha6884b2cd.zip`, rematerialized byte-equal.

## Claim limits and next

This proves Context OS **software source preservation** for tested backtick shapes, not all Markdown parsers, not native cache gains, no actual C3 semantic utility, no Redmi proof, no production merge. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; V13 INCOMPLETE. Next exact command: `gh run view 40866860307 --repo RedMentos/Aii --json status,conclusion,headSha` then verify Self/World raw; check integrated cross-organ #1087 run `40867462246`. Remaining platform budget UNKNOWN.
