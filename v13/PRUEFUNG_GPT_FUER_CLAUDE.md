# GPT/Codex review of Claude V13 work

## 2026-10-26 — Run484, WP-HX5 safety review (source-only)

Reviewed Claude branch `claude/project-thread-gqty8y` at `7585dd34ba82871a9842a557b505a08be887ce4a` (PR #480), specifically `v13/code/v13/agi/harness_data.py`, `harness_probe.py`, `harness.py` and their tests. Review branch `codex/run484-hx5-retention-failclosed-review-20261026`. The upstream branch is not overwritten.

**Confirmed bug 1:** `retention_gate({'learned_recall':.9,'base_recall':.2})` returned `RETENTION_PASS` despite missing every retention/forgetting/leak measurement. A minimal faithful reproduction of the original predicate also returned `RETENTION_PASS` with NaN candidate accuracy, forgetting and leak metrics. The fix requires finite bounded evidence and explicit `kl_checked` status.

**Confirmed bug 2:** `item()` used `if not record.get('accepted')`; the string `'false'` was truthy and would enter the training-data candidate. The fix requires `type(accepted) is bool`, rejects malformed messages and keeps genuine `False` excluded.

**Checks:** standalone original-predicate counterexamples reproduced in local Python; new adversarial tests `tests/test_run484_hx5_retention_failclosed.py` and inherited `tests/test_harness_data.py tests/test_harness_probe.py tests/test_harness_hx.py` are assigned to the source CI workflow. Full checkout test discovery was not performed by this reviewer because this container cannot resolve github.com; no claim of whole-repo GREEN. Run484 source CI Actions 40284124928: 41/41 PASS, privacy CLEAN; raw artifact 12632769941, ZIP SHA256 475a8ed94b97739d015078e6cdf6df298cfc6b720a5711f68eb9130a646ef522. This is not a full-suite or native proof.

**Limits:** no native models, no HX2 remeasurement, no dataset export or adapter activation. Claude's HX2 result stays `HX2_INVALID`; HX5 remains locked. STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA unavailable, `jepa_weight=0`, Redmi unmeasured. Open questions: external attestation of HX2_PASS file and human-only caller of `approve()` before any live integration.

## 2026-10-26 — Separate Run485 WP-HX2 probe integrity review

Review PR #483 is independent and edits only `harness_probe.py`, not this branch's `harness_data.py`. The original `compose({'V1':float('nan')},.5)` could return `CHOSEN`, and `paired()` silently intersected tasks and truncated unequal seed arrays. Run485 adds fail-closed INVALID_PROBE/HX2_INVALID handling and adversarial tests. Source CI Actions 40284364311: 32/32 PASS, privacy CLEAN; raw artifact 12633571014, ZIP SHA256 cd4b27074a66df2e600046add6b3af77e0a02234db945f6a701471bb176856d5. These separate PRs need coordinated review/integration; neither changes the historical HX2_INVALID finding or unlocks HX5.
