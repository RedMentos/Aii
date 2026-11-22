# Run11 cross-organ Age0 B-slot manifest fail-closed integration — prereg 2026-10-28

**Owner:** GPT-6 review-only child of #867, branch `assistant/v13-run11-world-c2-c3-ag0-slot-integration-20261028`, exact parent `89d584dc875f9ab36cfeb1b7d3874056d12a4261`. Parent F4 World, C2 benchmark and C3 prompt candidates retained, #867 full CI pending at prereg. No main merge or overwrite of sibling owners.

## Source / reason

- Independent sibling PR #846 (from #844) reproduced an actual Linux-native JEF no-B-manifest route failure: native 40632157217 `combined_c3=false`, despite C3 fallback intent. It also had synthetic RED 40632820503 (two stale AG0 slot failures), focused GREEN 40632940211 (11/11) after a fail-closed repair. The PR #846 `v13/bodies.py` blob `82fb81c8a98c51ca1c339737184e2fda8ab6a692` rejects stale ACTIVE/RAMP slot overrides when their installed base role is absent or disabled; `tests/test_bodies.py` blob `e71f6f7a0e0f5a5016d81f0ba17c4bb793e1f6e4`. Current parent blobs differ. Import **only these two exact disjoint blobs**, no runtime/focal rewrite, no model/seed/catalog changes.
- Sibling PR #845 C5 selection fix and #847 combined source are on another review chain with different `focal.py`/`runtime.py` hashes. This package does **not** claim C5 selection fixed or native JEF end-to-end GREEN. The #860 runtime C2 patch remains excluded because its full suite RED on frozen source hashes.

## Acceptance

After prereg import exact Git blobs and verify remote readback. Run source-pinned focused AG0 stale slot, World receipt, C2 scorer and C3 prompt tests plus complete Linux software suite/compile/privacy/diff. Archive raw stage exits and hashes, private byte-exact backup. Parent #867 and this combined branch must independently pass before any integrated software claim. Do not run heavy native models while another owner holds them; native end-to-end rerun and C5 integration remain separate requirements.

No STEP2/B3/Body-JEPA/LP3/jepa_weight/Age/whole-system promotion. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight0, Age0 RECORD_ONLY, Redmi unmeasured. Platform budget UNKNOWN.
