# WP-BP11 module lifecycle CAS: seven reproducible stale-authority races closed (review-only)

**Source:** five-parent integration PR #672 `9eae3cc175512382038cc5f55887e7a8dbc9797f`, not `main`. Review owner: GPT-6; only `v13/code/v13/modules_gate.py`, `module_learn.py`, new isolated tests/workflow and scoped proof changed. No frozen cohorts, original model/source/seed hashes or age rights changed.

**Original RED:** exact commit `b7706a33c67481cd91858876dbc7f270773f92bf`, Actions `40465079891`: 48 synthetic SQLite tests, **7 FAIL** (all newly introduced mid-call revocation/disable/halt cases), existing 41 PASS. Compile0, privacy CLEAN. Raw artifact `12716372213`, ZIP SHA256 `c5e856ec4ef3d98552db7917fc67b041c5d55886b50ea97458db2dd9fa1f3a8c`; CRC/HEAD/exits checked and private Library backup byte-identical.

**Intermediate RED:** exact commit `624224ac604728ba8e3c23d80ce547ff419c98f1`, Actions `40465226289`: 48 tests, **1 FAIL** (stale export after corpus), original failure retained; no claim of green.

**First GREEN:** exact commit `2f7f18f25078fb7f828a6866b52a036f0bd4d088`, Actions `40465244283`: **48/48 PASS**, compile0, privacy CLEAN. Original raw ZIP `12715509812` SHA256 `1ffd57ec50860d7368aaeb8a2f5bb932945f7116b4c495956ff1bc1cc73a8dfe`, CRC/HEAD/exits checked, private backup byte-identical. Source SHA256: `modules_gate.py` `125a373f26e82157fd6371c78e57d8717b1f52bae8d0f78f4f74183936e67e9c`; `module_learn.py` `58dd97fc7a8984803901539ab1e76d5d7de976bd44d3b560ed0296f70774dc36`; `test_module_lifecycle_cas.py` `d55541c050d8deb723fb3d63b42440c829ed41e8d6f4ad214880a72adc959059`.

**Behavior:** the proposal feature is checked again in the state mutation; quarantined check and release compare current state and digest inside optimistic CAS before changing state; release rechecks Notaus/typed bans after file read; corpus refuses stale version snapshots; export validates the module state version and re-reads tagged bytes before writing JSONL. These are deterministic adversarial callbacks, not claims of full thread safety or learned knowledge.

**Residual / next:** the final policy-check-to-filesystem-write interval is not transactional across tables and files. In particular, a revoke with `delete=True` during the quarantine write can leave a stale file; next package will preregister and test that exact window, preserve RED and close what is possible without weakening authority. Broad suite historical 5 FAIL/73 ERROR remains RED. No phone/native/model/network proof; no production merge. STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi unmeasured, full scope false.

**Resume command:** `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_module_lifecycle_cas tests.test_modules_gate tests.test_review666_module_halt_race tests.test_review666_bp11b_export_gate`.

**Private backups:** `/V13-Checkpoints/2026-10-27/Module-Lifecycle-CAS/`. Source/next command/negative gates also in `BUILD_STATE_MODULE_CAS.json`.

## Follow-up package: post-write authorization + ownership

Original preregistered RED `abe9abce1dca53ed5aa717a102a02660a86410ab`, Actions `40465483085`: **52 tests, 3 FAIL** (disable, Notaus, typed NETWORK ban). Revoke(delete=True) in the **post-write** callback already passed because revoke unlinked the file; the predicted failure for that ordering was disproved. Original ZIP `12716705293` SHA256 `0c596a446a3f06e97fdbfc85d0d35bba0d3110cd77dede54ae7ab402c9c7129e`, CRC/HEAD/exits checked and private backup byte-exact.

Source fix `b80120860c6b33edcd98fcd23f0c26e5699cf0d0` rechecks the typed policy after the quarantine write and inside the optimistic state mutation, and removes stale bytes only when no other fetch owns the state. Actions `40465545500`: **52/52 PASS**, compile0, privacy CLEAN; ZIP `12716552072` SHA256 `cc769ea0dcf131d08d44604fe27feb0f1359bee50fa72c5b70da10ed45d9dae0`, CRC/HEAD/exits checked, private backup byte-exact.

Two additional counterexamples test revoke(delete=True) **before** the file write and competing same-ID fetch ownership; source unchanged, tests `7a4734d8dea06036af1b83f319482006656e7f31`. Actions `40465641170`: **54/54 PASS**, compile0, privacy CLEAN. ZIP `12715713153` SHA256 `cf3bd885e13696824d708de15ef79500d8d290a3ae3e414ebb9b135548733b9f`, CRC/HEAD/exits checked, private backup byte-exact. Current source SHA256 `modules_gate.py` `3203460dce8db9a8b83f56635dfc52a73c610d5231a7bc8c744741c53e7c7714`, `module_learn.py` `58dd97fc7a8984803901539ab1e76d5d7de976bd44d3b560ed0296f70774dc36`, tests `61e8888f1b3f8d76e7d97014a19d65fc557f4b1ef43a28122cbe966d1f6443fe`.

New independent exact-source broad differential workflow `module-lifecycle-fullsuite-diff.yml` and source-only Termux ZIP/operator workflow `module-lifecycle-phone-source.yml` are queued/running; **their results are not yet claimed**. Existing full-suite historical 5 FAIL/73 ERROR remains RED unless the new differential proves otherwise. All raw ZIPs are in private `/V13-Checkpoints/2026-10-27/Module-Lifecycle-CAS/` with byte verification. Remaining cross-table final-check/filesystem TOCTOU is not proven absent.

## Closed independent broad and phone source evidence

**Broad differential:** Actions `40465809405` at exact source `36e5ec8b58f34bde2630b7a6aa9a0bb2f9eda42c` retrieved the original historical five-way 4,483-test artifact `12714654986` by ZIP SHA256 `1ff54f58f1e2e3a3c8aa92564a709dc4ae6bfcbaafbfcbc41675d83b90a90657`, compared every sorted FAIL/ERROR header without modifying the frozen baseline, and ran **4,496 tests**: **5 FAIL, 73 ERROR, 28 SKIP**, suite exit1. Exactly **78/78 historical headers unchanged, 0 new, 0 missing**, comparator exit0, compile0, privacy CLEAN. This is **HISTORICAL_RED_UNCHANGED, not a full-suite PASS**. Raw ZIP `12715784751`, SHA256 `2445ada234e37c70045bf41730ed4426a02870ab8a40a069f06633bce42b32d8`, CRC/HEAD/exits checked, private Library byte-identical. Historical source-binding, torch, Run147 and LP3 import prerequisites remain open; no test suppression.

**Exact phone source:** Actions `40465873749` at `fcafb0a0873eecba07f3ab193b0c1277df78b0fe`: source-only Termux ZIP SHA256 `7f7cbe5d20093db82b530677b8cbd636b3d999430a9bb856a43d10d9e37d15a7`, **1,417/1,417 member SHA256 and CRC PASS**, extracted **94/94 portable tests PASS**, persisted `:modul an|aus` operator smoke PASS, privacy CLEAN. No native model/Redmi execution. Outer raw+source ZIP artifact `12716127938` SHA256 `1492ea5661bef04a771d9ba24930b63e92f5a799bfb4994157f9296642fbbab9`, CRC/HEAD/exits checked, private Library byte-identical. Original negative gates embedded in ZIP: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, V13 INCOMPLETE.

Both ZIPs are privately persisted at `/V13-Checkpoints/2026-10-27/Module-Lifecycle-CAS/`. Next: independent PR #675 review, then stacked PR #676 direct recall ban and PR #677 BP1 source-bound consumer dataset; native C3 BP1 training remains a separate preregistered proof.
