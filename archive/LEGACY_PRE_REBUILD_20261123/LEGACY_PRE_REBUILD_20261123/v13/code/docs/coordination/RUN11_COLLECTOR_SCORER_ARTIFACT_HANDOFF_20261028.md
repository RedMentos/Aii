# Run11 STEP2 collector × scorer + model-artifact probe handoff — 2026-10-28

**Review-only branch** `assistant/v13-fourarm-collector-scorer-crossorgan-automation11-20261028`; PR #826 targeting the #825 review branch, **not main**. This is an interim durable checkpoint; update from actual completed CI results before promoting anything.

## Exact integration ancestry and ownership

- #825 parent `db1b5238e6e9193d62e1a75a38f545c3a28533df`; prereg `d7288491088919290a37c418817e749d1fefa161`; exact six-blob #824 merge `dadd544288ca8816f579390a3e30c86967b4f3ed` with second parent `c702bb536499f2479edeaad9ee2ef50a82efc7a2`.
- Owner: GPT-6 Run11 only this branch. No other owner branch, main, Canon or historical registration overwritten. No force-push or rejected Drive destination.
- Source `step2_fourarm_native_collector_candidate.py` exact imported Git blob `5722cdcf6163331ae83677bd96394399cca0fbc3`.
- `step2_longnote_fourarm_io.py` adds raw native two-report framing, verified 70-row digests, source fixture SHA, arm/seed/JEF query, preparation model/runner and utility/error-profile binding; native evidence requires an **independent expected fixture SHA**. SOFTWARE_SYNTHETIC remains diagnostic only.
- New `step2_current_catalog_artifact_probe.py` uses existing ModelManager into isolated scratch; no model weights or native inference have been downloaded/executed in this run yet.
- `specs/models.json` unchanged Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`; `v13/models.py` unchanged blob `bd035cf8029850cce00b179edf533e53bf24358a`. Current catalog B1=1.2B QAD, B2=Qwen3.5-0.8B, C3=350M QAD; historical 230M/1.2B PTQ alternatives NOT substituted.
- Canon `V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` unchanged blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.

## Closed evidence (no fabricated native runs)

- Corrected RED-only counterexample run `40621868536`: 2 native raw/summary mismatch tests fail as preregistered, `FOCUSED_EXIT=1`, artifact SHA256 `ee61e71414552b183600b2c28408ec4fe2b0173b397bb19622ffa53627697395`.
- Native fixture independent-pin RED `40622406879`: 20 tests, exactly one expected missing-pin failure; artifact SHA256 `75ff60bd9b7c0a994b998e4e2bcce808c48110a9414e6f0fdfc2b7a3810e765f`.
- Linux full suite GREEN `40621790204` at `0aa3fc2`: 36 focused, 2149 full (1 skip), compile/privacy/diff exits zero; ZIP SHA256 `45f1dd9306f8a629d6378e45ec679fa79df4e0ce2b77df5e9060f4c9f2ccf48d`.
- Linux full suite GREEN `40621844239` at `a490a23`: 36 focused, 2149 full (1 skip), all exits zero; ZIP SHA256 `a7cbe05ed8b0164b8807a6af965eba4df0221980b24c80e521bf9a6b8e3fa6d1`.
- Fixture external-pin quick GREEN `40622480325` at `0583f21`: 20 focused, all exits zero; ZIP SHA256 `ada6b92b45be45c11711f29acfcedd5e986fffb301a82dad743d3b1eec57d345`.
- Current-catalog artifact-probe quick GREEN `40622870876` at `27f34e8`: 25 software tests, all exits zero; ZIP SHA256 `be0632d89b27ea3ef056da71ee05e76a1a033baf29f35666a57229ddffb29c93`.
- Full `40622480390` (source `0583f21`) and `40622962708` (source `e929709`) still pending/in progress at this checkpoint. Check exact conclusions and preserve raw artifacts.
- Private Library backup: `/V13-Checkpoints/2026-10-28/Automation11-STEP2-Collector-Scorer-Integration/`; uploaded RED and GREEN raw ZIPs and byte-compared the initial batches. No public model weights.

## Negative gates and remaining blockers

STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, LP3 heldout `FAIL`, `jepa_weight=0`, Age0 `RECORD_ONLY`. These tests are Linux software/mock, not native inference or Redmi. No installed model/runner bytes, no device thermal/energy/RSS or cgroup ownership proof, no 12-run native evidence.

## Next exact commands and prerequisites

1. Review GitHub Actions run `40622480390`, then `40622962708`; download artifacts, verify all exit codes and ZIP SHA256, persist in the same private Library folder. If a test fails, preserve failure and fix on this branch only.
2. Run isolated software tests: `cd v13/code && PYTHONPATH=.:tests python3 -m unittest -v tests.test_step2_current_catalog_artifact_probe_20261028 tests.test_step2_collector_scorer_crossorgan_20261028 tests.test_step2_fourarm_native_collector_candidate_20261028 tests.test_step2_longnote_fourarm_analysis_20261028 tests.test_step2_longnote_fourarm_io_20261028`.
3. After heavy full CI owners release the runner, activate the already committed **manual-only** `.github/workflows/step2-current-catalog-model-byte-proof-20261028.yml` via an explicit branch-scoped push trigger. It downloads current pinned B1/B2/C3 only into ephemeral Linux scratch, verifies actual GGUF bytes and SHA, uploads **metadata/logs only**. Requires network and >2GB free scratch; no paid provisioning, no native inference, no model redistribution.
4. Native experiment is a later separate preregistration with actual installed B1/B2/C3/runner/source hashes, exclusive owner and resource budget; do not reuse old cohorts. Redmi proof requires the device operator.

**Actual platform budget remaining: UNKNOWN.** This is a checkpoint, not an end-of-run acceptance.
