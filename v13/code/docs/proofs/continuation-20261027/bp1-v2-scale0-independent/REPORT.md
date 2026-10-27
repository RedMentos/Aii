# BP1 V2 SCALE0: independent original native ZIP closure and negative heldout utility (2026-10-27)

Owner GPT-6, review PR #700 (child of PR #697). Exact native Actions [40490945294](https://github.com/RedMentos/Aii/actions/runs/40490945294), source `813458125cb98a0a9ad552305607e6155dee90a7`: original ZIP `12727819132`, SHA256 `ab102549b6a5538157572617f39e512e840a540bda683e502c7ab72c7b87f315`. Dataset original artifact `12715684803`, SHA256 `12a66c12019ee267cac12defd0b281f34fbcac5dc1f2e941236ae4ebf9a5f56c`. Both CRC PASS, original native exits all zero, 44 unique paired responses, 25-row FP32 QAD LoRA train, frozen source/model/runner/seed, nonzero LoRA-B (38,912), 2 optimizer steps. No weights uploaded.

Pre-registered `e23b7228223cea92af108a4da234aad56705f6ec` before integration. Imported **unchanged** four independently reviewed auditor/scorer/test Git blobs from PR #691, exact parity checked in CI. Independent [Actions 40494191600](https://github.com/RedMentos/Aii/actions/runs/40494191600) exact `9a1fa82891ea85ef059dcfce9527164b2f1ddc08`: **17/17 adversarial tests PASS**, SHA/CRC/HEAD/native exit/model/adapter/train proof/44-response source+prompt binding/duplicate guard/independent quote rescore all PASS; compile0, privacy CLEAN. Raw audit ZIP `12729836741`, SHA256 `0bfaed8c6a315694e4ff58c7ba6787f79b6d4017d2efcaa3a1ba4c8af2ffcbda`. Both native and audit original ZIPs stored privately in `/V13-Checkpoints/2026-10-27/BP1-QAD-V2-SCALE0-40490945294/`, re-materialized and compared byte-exact. Original prior RED runs remain preserved on their own branches; this does not erase them.

## Independent measured outcome (11 source-disjoint heldout pairs)

| Model | No B2 offer supported | With B2 offer supported |
|---|---:|---:|
| Base QAD Q4 | 0/11 | 2/11 |
| Same base + trained 2-step LoRA | 0/11 | **0/11** |

The candidate loses both supported offer cases (2 losses, 0 wins, 9 ties). Training CE 0.90984→0.64171 is a **train-only improvement**, not downstream benefit. Native execution is verified, but **C3 learned source-quote utility is not demonstrated**. No claim about general model quality from 11 pairs; no new heldout or model training in this audit.

## Negative gates / next action

STEP2 `UTILITY_FAIL`, B3 `L1_FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Redmi sustained proof unmeasured, full V13 incomplete. No runtime/default/approval/model weights changed. Next: a *new* preregistered source-disjoint near-miss/retention native evaluation or separately designed objective ablation, preserving historical model/source/seed hashes. Independent work on other canonical organs can proceed without waiting for a native job.
