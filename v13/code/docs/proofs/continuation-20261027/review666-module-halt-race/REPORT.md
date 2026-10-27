# Independent Claude PR666 cross-review — in-flight module revocation (2026-10-27)

## Source and ownership

Base `ed5010708bdb3d11c5e495f01cc07d99d359ba39` (Claude PR #666, review-only; itself stacked on PR #665's **disposable harness source**, not on a committed AG5/World resolved runtime). Our isolated branch `codex/v13-review666-module-halt-race-20261027` changes only `v13/code/v13/modules_gate.py`, a new five-plus-two-case test module, isolated workflow, and scoped evidence/review documents. No main/Claude-branch overwrite, no native/model/Redmi or authority/age change.

## Confirmed defect and counterexamples

The original module fetch checks Notaus/typed prohibitions/user rules only **before** a potentially 20-second network operation. An injected fetcher that turns on Notaus, adds a NETWORK ban, or adds the user's own download FORBID while it runs returned data which the original implementation still persisted and promoted. A further source audit found the human can revoke the proposal or turn modules off during the fetch; the old unconditional `_to(QUARANTINED)` resurrected the withdrawn state.

Preregistration `c6204280ef1442499a447ea81061f8f7c0660994`, first tests `05f645550edf01e41879993613ca10d4bf850535`. **RED 1** Actions `40459519547` at `72c69da5864ecf297519e98bfda33f0ece1dd95b`: 43 tests, 3 FAIL (Notaus, NETWORK, user-rule), compile0, privacy0; original ZIP artifact `12712954630`, SHA256 `44f801435b9667d19f3c59ad6306db6937868424070044cc87c41958893c4401`. Amendment `f6fb9e25715b16ff7888eeccab880a0dc3be65f9` preceded two new tests at `9c497975ce7ea3d76715226cc7e8ba8384302468`. **RED 2** Actions `40459657917`: 45 tests, 5 FAIL (adds revoke/disable), compile0, privacy0; original ZIP artifact `12713254263`, SHA256 `d63a3fe55c7570a42d011e62a78ed540802647a57a84c9c2634f98ac06edb4c9`.

## Fix and proof

Source commit `255fb7c73b161cc9ae95b11b4575d1a9def3c45b`: re-read enabled/proposal state and fixed safety rules **after external I/O, before any quarantine write**. The eventual StateBox transition also verifies that the proposal is still enabled and PROPOSED. No network or real module was fetched; all cases use injected in-memory synthetic JSON. Unaffected authorized fetch remains SANDBOX_OK.

**GREEN** Actions `40459751403` at exact source commit: **45/45 PASS**, compile0, privacy CLEAN, ZIP artifact `12713857387`, SHA256 `da34e376e8fae690c8d6b9f985a5bf43ecf01a303ee1411584959d82942982b6`. All three ZIPs CRC clean, HEAD and exit receipts inspected; backed up privately and independently byte-reverified under `/V13-Checkpoints/2026-10-27/Review666-Module-Halt-Race/`.

## Independent integration findings and limitations

- **BLOCKING for AG5+World integration:** PR #666 is based on PR #665's **unmerged disposable merge harness**, not the resolved two-parent runtime. Its `operator.py` still lacks AG5's `:language` command, uses unbounded `:chats`, and allows `:effort` mutation without AG5's `r.lock/r.require_idle` guard. This is not proof that Claude overwrote AG5; the AG5 runtime was never present in that branch. Do not call the chain integrated or merge it to main until a tested resolved integration commit is actually based in.
- PR #666 includes generated `__pycache__/*.pyc` files; remove these from the eventual integration branch and use a targeted privacy/diff check.
- Qwen3Guard local `trust_remote_code=True` path is not pinned/verified in code and has no real native/Redmi runtime test; keep off and UNVERIFIED. The module's license is self-declared by JSON, not independently proven.
- **Residual concurrency limit:** no cross-process transaction spans network I/O, filesystem rename and SQLite. A change between the last gate check and the file write can leave a quarantined orphan; the guarded state transition prevents one class of resurrection, not a global linearizability proof. Further review of `check`/activate races is open; do not promote M1–M8 to fully proven.
- Existing STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, native/Redmi and full-scope negative gates remain.

## Next command / owner

Independent reviewer: GPT-6 on isolated branch. Next reviewer/merger should first resolve PR #665's disposable CI and build an actual AG5+World integration review branch; then rebase/integrate PR #666 and this patch with full suite and cross-feature tests. Focused replay:

```bash
cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_review666_module_halt_race tests.test_modules_gate tests.test_guard2
```

No user action required for this isolated fix. Whole-system acceptance remains incomplete.

## Subsequent Claude BP11b integration review — 2026-10-27

After original PR667 GREEN, Claude PR666 advanced independently to `e505364c78d6ef222eb287d84d84aed81ecc53e3`, adding `module_learn.py` and recall/export tool wiring. Our original review branch had not tested that new source. Prospective amendment `AMENDMENT_CLAUDE_BP11B.md` preceded an exact disposable, **zero-conflict** merge of our fix and that new Claude head; no remote merge commit, no owner overwrite. Actions **40460531847** at review head `da218259b1f8f2ca07b13e56ca0c8793ef84d1bb`: **50/50 synthetic tests PASS**, compile0, ephemeral commit0, privacy CLEAN, no merge conflicts. ZIP artifact **12714845067**, SHA256 `437bbbc08f5ec48541d751f8637c9af4aa8dc36927603b96930065c2ea56b467`, CRC clean, exact HEAD/exits inspected, privately saved and byte-reverified under the same Review666 folder. This proves BP11b + our fetch-revocation patch can coexist in this disposable Linux synthetic tree; it does **not** prove module retrieval improves model answers or that PR666 contains the AG5 resolved runtime.
