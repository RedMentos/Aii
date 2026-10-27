# WP-BP11 module lifecycle CAS: seven reproducible stale-authority races closed (review-only)

**Source:** five-parent integration PR #672 `9eae3cc175512382038cc5f55887e7a8dbc9797f`, not `main`. Review owner: GPT-6; only `v13/code/v13/modules_gate.py`, `module_learn.py`, new isolated tests/workflow and scoped proof changed. No frozen cohorts, original model/source/seed hashes or age rights changed.

**Original RED:** exact commit `b7706a33c67481cd91858876dbc7f270773f92bf`, Actions `40465079891`: 48 synthetic SQLite tests, **7 FAIL** (all newly introduced mid-call revocation/disable/halt cases), existing 41 PASS. Compile0, privacy CLEAN. Raw artifact `12716372213`, ZIP SHA256 `c5e856ec4ef3d98552db7917fc67b041c5d55886b50ea97458db2dd9fa1f3a8c`; CRC/HEAD/exits checked and private Library backup byte-identical.

**Intermediate RED:** exact commit `624224ac604728ba8e3c23d80ce547ff419c98f1`, Actions `40465226289`: 48 tests, **1 FAIL** (stale export after corpus), original failure retained; no claim of green.

**First GREEN:** exact commit `2f7f18f25078fb7f828a6866b52a036f0bd4d088`, Actions `40465244283`: **48/48 PASS**, compile0, privacy CLEAN. Original raw ZIP `12715509812` SHA256 `1ffd57ec50860d7368aaeb8a2f5bb932945f7116b4c495956ff1bc1cc73a8dfe`, CRC/HEAD/exits checked, private backup byte-identical. Source SHA256: `modules_gate.py` `125a373f26e82157fd6371c78e57d8717b1f52bae8d0f78f4f74183936e67e9c`; `module_learn.py` `58dd97fc7a8984803901539ab1e76d5d7de976bd44d3b560ed0296f70774dc36`; `test_module_lifecycle_cas.py` `d55541c050d8deb723fb3d63b42440c829ed41e8d6f4ad214880a72adc959059`.

**Behavior:** the proposal feature is checked again in the state mutation; quarantined check and release compare current state and digest inside optimistic CAS before changing state; release rechecks Notaus/typed bans after file read; corpus refuses stale version snapshots; export validates the module state version and re-reads tagged bytes before writing JSONL. These are deterministic adversarial callbacks, not claims of full thread safety or learned knowledge.

**Residual / next:** the final policy-check-to-filesystem-write interval is not transactional across tables and files. In particular, a revoke with `delete=True` during the quarantine write can leave a stale file; next package will preregister and test that exact window, preserve RED and close what is possible without weakening authority. Broad suite historical 5 FAIL/73 ERROR remains RED. No phone/native/model/network proof; no production merge. STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi unmeasured, full scope false.

**Resume command:** `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_module_lifecycle_cas tests.test_modules_gate tests.test_review666_module_halt_race tests.test_review666_bp11b_export_gate`.

**Private backups:** `/V13-Checkpoints/2026-10-27/Module-Lifecycle-CAS/`. Source/next command/negative gates also in `BUILD_STATE_MODULE_CAS.json`.
