# Run287 — atomic source-revocation gate (2026-10-25)

## Ownership and tested source
- Base: PR286 proof head `bc1944b665b918da8b45563b73dc331902fc9a49`. Exact tested source head: `c956e47fff2de03ed89a2cd78ff98c67b4fb02e6`. PR287 remains draft and is not merged into old main.
- Owned: `v13/store.py` (narrow `switch_generation` transaction guard), new `tests/test_revoked_update_lineage_run287.py`, dedicated CI and this proof. PR284 Runtime owner untouched.
- Canon SHA256 unchanged: `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`.

## Concrete defect and implementation
- A `SHADOW_TRAINING` worker can observe an explicit human source before publishing `source_ids` into its update manifest. A concurrent `:forget` then cannot find/quarantine the not-yet-published dependency. Previously, a late `PENDING_APPROVAL` could pass `Store.switch_generation` with the revoked source.
- Run287 checks every published candidate `source_id` for a live SQLite row **inside the same write transaction as generation approval**. It also reads the registered source blob (including archived form) and verifies SHA256 before commit. Missing, revoked, malformed, corrupted or absent lineage fails closed. The original retention, stability, authorization, model revision and approval gates remain unchanged.
- Primary source: SQLite official isolation and transaction documentation, https://www.sqlite.org/isolation.html and https://www.sqlite.org/lang_transaction.html — `BEGIN IMMEDIATE` acquires write authority before validation and serializes competing writers. This is a SQLite write-transaction claim, not a guarantee against an external filesystem attacker replacing a blob after validation.

## Closed evidence
- Exact source `c956e47fff2de03ed89a2cd78ff98c67b4fb02e6`:
  - Run287 dedicated CI `40195008742`: **50/50 PASS**, compileall PASS, official privacy CLEAN. Raw artifact `12598984125`, independently downloaded SHA256 `753a0cc024d6413b5e93fe75e4695c73ca96a83f3fff9d67a9ab3c6a263341e3`.
  - Persistent multi-chat operator journey `40195008770`: **PASS**.
  - Focused source-bound CI `40195008670`: **401/401 PASS**, extracted runtime/restart **114/114 PASS**, privacy CLEAN, 1000 registered phone source files, independent ZIP SHA256 `e98c811e153722e483a3e8112401060d0f2b685f2e2e22cd4354bc5a5861514c`. Outer source artifact `12599586375`, SHA256 `9bb7744f2b1739e2c02d8425ac3ca09a7dcbe63023a1a664ff5b3ffeb26c56f1`.
  - Independent local SQLite tests: **50/50 PASS**.
- Source blobs: `v13/store.py` `4fa1d8858412d739ffddb3509d711e4523cb2c0b`; `tests/test_revoked_update_lineage_run287.py` `3f2d2040d48302108bdd9340518d01ab0b94f8d0`.
- Exact source archive and raw CI ZIP additionally saved in a private ChatGPT Library checkpoint, downloaded back and SHA256 compared. Rejected anyone-writable Drive destination not used.
- Prior intermediate attempts `eed36700` and `d7f58c29` remain in remote history and Actions logs; none were overwritten or called a final native proof.

## Scope and remaining work
- **SQLite/Linux-software only.** The candidate artifacts in this test are synthetic, not native weight updates. No Redmi run or full native V13 acceptance is claimed.
- Unchanged: `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `jepa_weight=0`, `V13=INCOMPLETE`. Run282 separately proved four registered STEP1 native checks; the older Run269 full native suite was 12/20 and must be refreshed on the current integration chain.
- Exact next: run one serialized full pinned-native acceptance of the newest chain (all registered stages, no `--quick`, no altered cohort), archive every stage and negative gate; then implement the highest-utility failing canonical component without modifying PR284's active Runtime ownership.
