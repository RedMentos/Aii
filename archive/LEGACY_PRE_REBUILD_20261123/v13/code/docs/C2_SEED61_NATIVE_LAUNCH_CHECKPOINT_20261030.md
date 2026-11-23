# Seed61 Linux-native launch checkpoint — 2026-10-30

**Branch-scoped review only; no merge, no gate promotion.** Source prereg commit `8713ee286a6a20a777ce266a557b316c46599429`; exact native workflow launch head `5ac90444fe2e0317a954cb4ed94730900b33d92c` on `assistant/v13-seed61-isolated-body-postclose-20261030`. Current owner: GitHub Actions native job; do not start another heavy native/model job while this job owns the serialized `v13-step2-budget-paired-native-20261030` concurrency group.

## Prerequisites verified before native

Source-only exact-source recheck Actions `41007663414` at `bb61c0d21278f48f2f0fa2f2ddc0f152bb8860be`: **GREEN**, 12/12 software tests, actual import and frozen simple scaffold PASS, prereg/source/test/canon/model/control pins PASS, privacy/diff PASS. Original artifact `12955639430`, ZIP SHA256 `66098f8456aec42f9d9044f4d70d9e836034d4db0e98ce65e281f0aeba1d956e`, CRC clean, 20/20 SHA256SUMS, all 9 stage exits zero. Private Library backup `/V13-Checkpoints/2026-10-30/Run12-Seed61-IsolatedPostclose/CI_GREEN_RECHECK_41007663414_sha66098F.zip` re-materialized and SHA256 byte-identical.

## New native run

- **GitHub Actions run `41007813416`** — workflow `.github/workflows/v13-c2-isolated-seed61-native-20261030.yml`, source-pinned, serialized; **IN_PROGRESS at launch checkpoint**. 24 independent fresh Age0 turns, 6 arms, 4 unseen project fixtures, frozen source-bound scorer. Native model dependencies installed by isolated runner. It is a Linux-native candidate only, not Redmi.
- Workflow preserves all stage exits, raw event/OfferPacket/runner/C2 context, pre- and post-close process release receipts, PID bindings, original failure rows, negative gates, model/catalog pins, privacy/diff, SHA256SUMS, and original ZIP artifact on PASS **or RED**. Independent raw verifier replays `row_evidence` and score from persisted source-bound evidence.
- Exact next command after run terminal: query `41007813416` jobs and artifacts, download original ZIP, verify GitHub digest, ZIP CRC, every inner SHA256SUMS and stage exit, check all 24 raw rows and any native failure; privately back up original ZIP, re-materialize and verify SHA256, update scoped BUILD_STATE. **Do not** label a failed pilot GREEN. Continue independent canonical packages while the heavy job runs.

**Gates unchanged:** Age0 `RECORD_ONLY`; STEP2 `UTILITY_FAIL`; B3 `NO_PROMOTION`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; Redmi `UNMEASURED`; whole V13 incomplete. Platform budget UNKNOWN.
