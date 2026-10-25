# Run203 BUILD_STATE — Source-bound human correction recall (2026-10-25)

## Parent, ownership, canonical scope
- Parent Run202 PR230 `3a63cb85a5cf2c45f8ba06885d12ddc504a2a076` (verified World RED/GREEN and focused source CI). Run203 PR231 branch `codex/memory-key-lineage-run203-20261025`.
- Independent owner: `v13/code/v13/memory.py`, new `tests/test_memory_recall_key_lineage_run203.py`, dedicated workflow, this proof folder. No edits to active native B2/C3, Age, World, ContextOS, JEF, Phone or model cohorts.
- Canon v10.16.1 and user requirements preserve exact human correction source, memory provenance, no cross-entity/session retargeting, human authority and Age-0 gates. Canon original blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` untouched.
- Evidence class: **software/synthetic actual Runtime/SQLite**, not model inference, Redmi or demonstrated learning utility.

## Actual-source RED and adversarial cross-review
- Original source at prereg commit `b8201e81d959457a057f6783e7288d37ac522ffe`: local 6 tests, **5 FAIL**; GitHub Actions `40176091271` / job `121116971206`: **33 tests, 5 FAIL**.
- Root cause: lexical `Memory.recall` checked only value SourceRef, but trusted mutable `memories.key_text`, `kind`, `scope`; deleting or rewriting the original `MemoryRecord` packet did not block recall. A Project Alpha human correction could be presented as Project Beta's fact.
- First fix commit `ed9e07721396f8ff07f0dc6679b133dc5bd1f158` passed original 33-test CI `40176136497`; independent review found a second gap: changing `memories.session_id` redirected a correction to a different session.
- Added tests at `638c43b4434ed175c504d04ccfa1b08844e89124`; GitHub Actions `40176180213` / job `121117243717`: **35 tests, 1 FAIL** (session retarget). All RED attempts and raw CI logs retained at their run/job URLs.

## Correction, GREEN and latency
- `Memory._verified_rows` now checks each active memory row against its original `MemoryRecord` packet for event, kind, scope, key and exact value SourceRef **before local/global precedence and semantic ranking**. Duplicate/missing/corrupt packets fail closed. The read path creates no new MEMORY_KEY source.
- `Memory.recall` query additionally joins original `events` by event id **and session id**, preventing ownership retargeting. No learned value, new authority, config or native inference.
- Exact source Git blob: `51debfb1262136a6765a67fb1306b0eca58594c2` → `a6f6dc0d941f939809f8d74b4d42f5d6314a0cb5` (local Git hash and remote bytes match).
- Final GitHub Actions `40176241926` / job `121117424998`: **35/35 PASS**, compileall PASS, official privacy scan CLEAN. Dedicated Run103 user-rule workflow `40176241929` SUCCESS. Focused source CI `40176241959` launched; verify final outcome independently.
- Local additional tests: **26/26 PASS** memory/semantic/route/executive; **37/37 PASS** memory user-rule/trainer/sparse/episodic. Linux synthetic latency for 300 corrections: 5.5 ms with lineage scan vs 2.1 ms without (single local sample, **not Redmi**).
- Raw evidence: `https://github.com/RedMentos/Aii/actions/runs/40176091271`, `https://github.com/RedMentos/Aii/actions/runs/40176180213`, `https://github.com/RedMentos/Aii/actions/runs/40176241926`, and `LOCAL_CROSSREVIEW.log`.

## Gates and next exact step
- STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; DS2 H2 `FAIL`; whole V13 `INCOMPLETE` unchanged. Age 0 and explicit human learning permissions remain.
- Verify PR231 remote head/owned blobs and focused CI after this documentation commit. Then move to a **functional end-to-end second-turn correction-to-C3-context integration proof** (source -> Memory -> Runtime -> C3 prompt, restart and forget), using a clearly labelled software test double; do not claim native quality. Initial local model-free probe already showed first response 'unknown' and second '120 Euro' only when the human correction entered C3 system context.
- Recheck latest Claude/Codex heads and active owners; do not overlap native work. No rejected Drive destination use. No user decision needed.
