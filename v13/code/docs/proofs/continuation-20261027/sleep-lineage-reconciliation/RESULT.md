# Sleep A / Context OS source-lineage reconciliation — verified software result

Date UTC: 2026-10-27. Review-only PR #792; base PR #791 exact `6c5dbf145380956ac29bf2d5479ec489ebc7ef5a`. Prereg remote commit `c4c921c102448719f8bf65b9888899b69d871df0` predates source/test commit `5641bf515bdba16f51f1339db1553d14ab7eb066`.

## Exact reused source
- `sleep_offline.py`: Git blob `e51766478fee915824853da7c8e73785b12e91b3` from previously verified Run207/208/278 chain. Validates stored digest source/event/message lineage before live C3 context, operator `:sleep digest`, and offline TTT staging.
- `history.py`: Git blob `a7138080e19b439331bf4c5da68e7e62f823f169` from prior Run53 strict complete-pair/source/session review.
- Four unchanged prior test blobs: Run205 `b0119e70b492c2b386979daf0c9e08cf438e2608`, Run207 `783092f081ede8fbfb8de3fd9879816b560f2fb4`, Run208 `b80eeacc38375368d35bdb8041f52ec42a70cbc2`, Run278 `947286a7e2debd2795c77bf1efe1a2fa98000fe5`.
- All six source/test Git blob IDs independently fetched from this PR branch and matched. C1, B3, World, HX, AG8 and Sleep A exact-ID source left unchanged.

## New exact-head Linux software proof (not native/Redmi)
GitHub Actions run **40599024941** at exact commit `b26ee564584c330d1e9911ea5d547c9d15ccc92b`: **SUCCESS**. Focused actual Runtime/SQLite + synthetic C3 tests **24/24 PASS**. Full software discovery **2048 tests OK, 1 skipped**. Raw exits `BLOBS=INSTALL=FOCUSED=FULL=COMPILE=PRIVACY=DIFF=0`; privacy scan `CLEAN`. Artifact ID `12778325365`, ZIP SHA256 `f223062eac8efa95486b37807704104ca7a07f7a53e0bf0b62547b6b019e73ab`, ZIP CRC **PASS**, all embedded `SHA256SUMS.txt` entries **PASS**. Original raw artifact uploaded to private Library `/V13-Checkpoints/2026-10-27/Automation11-Sleep-Lineage-Reconciliation/v13-sleep-lineage-40599024941.zip` and materialized back: byte-for-byte identical, same SHA256. The original GitHub artifact remains available on the run. Historical RED failures of prior PRs remain unmodified.

## Claim boundaries
The run tests source-integrity and software behavior only. It does **not** show new semantic utility, native inference, sustained Redmi performance, learned JEPA weights, training or production integration. Original negative gates remain: STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; jepa_weight `0`; Age/approval authority unchanged; whole V13 incomplete. Review branch must not auto-merge.

## Independent review and next work
Review this exact-source integration against PR #791, including whether the stricter `native_history` behavior interacts with any current-source consumer not covered by tests. Next command: `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_sleep_ttt_source_lineage_run207 tests.test_sleep_digest_live_lineage_run208 tests.test_sleep_digest_view_authority_run278 tests.test_sleep_memory_c3_continuity_run205 tests.test_sleep_offline tests.test_history_lineage tests.test_sleep_a_exact_recall_identity_review`. For full software suite: `PYTHONPATH=.:tests python -m unittest discover -s tests -p 'test_*.py' -q`. Real device/native proof remains separately required. Sibling PR #793 F1/F5 memory and episodic route authority is independent and requires its own exact-head evidence; do not conflate results or merge siblings without a new integrated full-suite review.
