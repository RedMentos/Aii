# P2X 16×4 original native run 40870114898 — preserved workflow RED and repair prereg (2026-10-29)

Owner GPT-6. Original [Actions 40870114898](https://github.com/RedMentos/Aii/actions/runs/40870114898) on exact head `95bb1da99cfc8f5c35fc434bec7af3b0809db73d` **conclusion FAILURE**, not GREEN. Original ZIP SHA256 `0c00bae349613c085776b4ecb5e658100c586c26431e78854172ede0b003c952`; independent ZIP CRC CLEAN, **43/43** internal SHA256SUMS matched, all 16 recorded stages `SOURCE RESOURCE COHORT COHORT_SHA VENV TORCH DEPS PIP_CHECK MASTER_DOWNLOAD MASTER_SHA LICENSE_DOWNLOAD AUDIT INDEPENDENT_AUDIT ADAPTER_COPY PRIVACY DIFF` exited 0. Original raw ZIP privately stored at `/V13/RawEvidence/2026-10-29/P2X/fourstep_native_WORKFLOW_RED_40870114898_sha0c00bae3.zip` and rematerialized byte-equal. No rejected Drive destination used.

## What really failed

The final workflow enforce Python assertion was copied from the **eight-example one-step** predecessor:
`assert x['schema']=='v13.p2x.c3_lora_pilot.v1'`.
The actual registered 16×4 script correctly emits `v13.p2x.c3_receiver_fourstep.v1`. GitHub job logs show `AssertionError` on this exact line, after raw artifact upload. **Do not rewrite the original failure.** The narrow prospective repair is to replace only the final expected schema literal and misleading final step label. Keep original native source, model hashes, seed, cohort, steps, artifact hashes, negative gates, and full raw evidence unchanged.

## Original actual Linux-native evidence (narrow, not a utility gate)

Original `RESULT.json` records 16 unique frozen training projects, 4 A/4 B/4 NONE/4 UNKNOWN; four optimizer steps, rank2 v_proj/out_proj, 83,968 trainable parameters, jepa_weight0, alpha4, QAD FP32 master SHA256 `1d90518482c4ec204bebb4820bbaee4f8a38c5a6df72256f86bcd21fe52ad079`, frozen train SHA `af191c087d872a42924f2d2d465a3f26f6c323bf48c5c0682b30094b9d666cf1`. Reported per-step CE: **2.18928 → 1.86136 → 1.60191 → 1.41532**; in-sample master recall **0.375 (6/16)**; 146.49s reported trainer time, 2371.6 MB peak RSS on Linux x86_64 (not Redmi). GGUF adapter SHA256 `f5c25f7ea1c0ae727229bbd280857eb145ed01950ca640c800bd51d64fc9aebe`; PEFT safetensors SHA256 `0ecceccc43559a2c749ef23721ce5176d5e3b3832de8cac91d1ae748e642c6f3`. Independent offline `INDEPENDENT_AUDIT_EXIT=0` and original license/modified notice retained. This shows a bounded experimental fit and adapter artifact, **not** heldout source-use gain or deployed GGUF parity.

## Repair / replay acceptance

Commit this RED result before workflow repair. Re-run same frozen 16×4 protocol only after changing the one stale workflow assertion (no new cohort/model/seed/weights). Compare original and replay CE/adapter hashes and preserve any difference as a reproducibility result; independently audit the new raw ZIP and private backup. Do not claim GREEN unless all native and final workflow gates pass. No AG6/production activation; STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, Redmi unmeasured, V13 INCOMPLETE. Candidate360 heldout evaluation remains separate and not yet authorized to consume the frozen validation oracle for tuning.
