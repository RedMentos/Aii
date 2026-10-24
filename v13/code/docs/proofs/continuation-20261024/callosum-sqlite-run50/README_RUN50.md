# Run50 — Callosum SQLite source-bound outcome credit (isolated)

Preregistered before testing at commit `4b173fc2d14b9a7059c666882585b0966b180f2b`. Based on Run49 prereg head `b5de86ad417f157cb16e3af90d2dd302547cf4a3`. Only this folder owned. No frozen runtime, Canon, Run49, native model or Age rights changed.

## Independent source review

Production `v13/code/v13/callosum.py` Git blob `0dbe893a983a2739bb9e008e8a0c3fab5715aec3` selects first receiver OfferPacket after MessagePacket without checking `peer_message_packet_id`. Production `v13/code/v13/cognition.py` blob `1a9eb6f7c7cbfce83d91cc09b4ff9516cff310cf` emits that field on OfferPackets. This is a **source-level misattribution risk**, not a demonstrated real-runtime exploit. Store blob `0779d986fb8aee8aa01c5df5f656889d4bd56348`; Run43 candidate blob `9518a7127af5928b39a3fbab2d58b71597eaa737`.

## Candidate and evidence

Isolated `scripts/sqlite_outcome_candidate.py` executes a single `BEGIN IMMEDIATE` transaction over on-disk SQLite `states` and `packets` tables matching original column schemas, verifying event/generation/packet/role/channel/direction and `peer_message_packet_id` before credit. It preserves the original utility formula and updates, marks only actually credited messages, and refuses duplicate pending IDs. No production integration.

Initial **18/18 PASS**. Added adversarial peer-binding checks: **19/21 PASS, 2 FAIL** before fix (preserved). After fix **21/21 PASS**, then crash-after-commit/no-receipt regression **22/22 PASS**. Optimized Python **22/22 PASS**; compileall PASS. Includes eight racing SQLite connections and a fresh child process. **Synthetic packet inputs, Linux SQLite only**; no actual Store/Runtime, native Bodies, Redmi or full suite.

Closed source, tests, red and green raw logs are in `run50-code-raw.part1.txt` through `part3.txt`. Concatenate without separators, base64-decode, Brotli-decompress, untar in a disposable directory. SHA256 of decoded `tar.br`: `f422ed0529af519d40dde2eb7c5f3aa56bfd852dcc0c9e99431fbd0f54121956`. Each part's Git blob was remotely re-read and verified against local originals. Python `brotli` or `brotli --decompress` required to decode archive, **not** to run tests. Reproduce: `python -m unittest discover -s tests -v`.

Primary technical sources checked 2026-10-24: https://www.sqlite.org/lang_transaction.html, https://www.sqlite.org/wal.html, https://docs.python.org/3.13/library/sqlite3.html.

## Open / gates

Real Store coordinator lock, `Callosum._mutate`, `neuromod.step/touch`, actual OfferPacket provenance and `on_rating` are **not** integrated/tested. Source revocation after already committed credit is not reversed. Full checkout and official privacy scanner blocked by container GitHub DNS; remote GitHub connector worked. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE. Next: independent full-checkout review; real Store/Runtime duplicate-outcome/restart tests, then integrate only if all existing gates and tests preserved.