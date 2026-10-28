# Run11 C2 transfer64 paired audit — 2026-10-28

**Scope:** Independent, review-only, offline replay of previously verified Linux-native PR #857 raw rows. No new native inference, no model or prompt change, no learning and no route promotion. This child is based on PR #857 head `849166ec1842d3ea3390ba782573410a9e93c044`; source and original evaluation cohort are unchanged.

## Input byte evidence

- Private original native ZIP: `C2_TRANSFER64_NATIVE_PASS_40640371815_sha26cc4e5d.zip`, SHA256 `26cc4e5da5f1d2a9e93d224573de9957db0a25206b50cf2e62910f900b3eaa2a`. ZIP CRC clean and all **21/21** SHA256SUMS entries match. BENCH, GO, PRIVACY, DIFF exit 0.
- Frozen fixture Git blob `e9aaae43f3313fbdc8e4b2fc870f2712a5557a66`, items SHA256 `12863402ffecef7565d23d1162fa061a1983ee92b46332c60adcfb3cd37ca9af`. The private Library copy had a trailing newline, so its blob was initially different. Removed only that final newline in the **local replay copy**, verified the resulting Git blob exactly equals the registered repository blob; no source or registered cohort was modified.
- Extracted `needle.rows.json` SHA256 `469cb9d5076d3dfbdae164bc13b042ffa729db7a933814ad6b58fe245122be7b`; `scaffold.rows.json` SHA256 `a2472e76c5be6c748a0c7f6c0a44df7b7689bf6eddc48ad87751763d6cf3e05b`. Both 64-row input files verified against their explicit hashes before pairing.
- Closed derived report SHA256 `1230971ba7abc9c9433a24727c106645a0da8ba81c0700ca271d644b8d5ccf58`; private Library destination `/V13-Checkpoints/2026-10-28/Run11-C2-Paired-Audit/paired.audit.json`. Raw native rows remain in the prior private ZIP, **not** in public Git.

## Paired author-labelled outcomes

| Cohort | N | Needle correct | Scaffold correct | Needle only | Scaffold only | Both correct | Both wrong | Scaffold minus Needle accuracy | Exact McNemar p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Overall | 64 | 19 | 42 | 8 | 31 | 11 | 14 | +0.359375 | 0.00029408 |
| English | 32 | 10 | 21 | 5 | 16 | 5 | 6 | +0.34375 | 0.02660 |
| German | 32 | 9 | 21 | 3 | 15 | 6 | 8 | +0.37500 | 0.00754 |
| simple | 16 | 2 | 16 | 0 | 14 | 2 | 0 | +0.87500 | 0.000122 |
| detail | 16 | 8 | 9 | 3 | 4 | 5 | 4 | +0.06250 | 1.0 |
| gist | 16 | 5 | 9 | 3 | 7 | 2 | 4 | +0.25000 | 0.34375 |
| both | 16 | 4 | 8 | 2 | 6 | 2 | 6 | +0.25000 | 0.28906 |

The exact conditional-binomial McNemar statistic describes disagreement on these **fixed paired author labels**. This is **not** an independent replication: same PR #857 evaluation rows and single Linux execution, not independently adjudicated gold labels. Language/class slices are exploratory and not multiplicity-adjusted. The p-values cannot establish deployment utility, generalization, confidence calibration, causal benefit, or Redmi performance. The native Needle confidence AUROC remains the original negative 0.4772; never use raw confidence for approval or action authority.

## Software and failure ledger

- New `scripts/c2_pairwise_transfer_audit.py` uses standard library only, pinned fixture bytes, explicit input SHA256, exact ordered IDs/labels, finite numeric checks, native validity, no-overwrite fsynced report and nonpromoting gates.
- **7/7 focused local synthetic tests PASS**, `compileall` PASS, plus actual closed raw replay completed. This is **not** a full Linux software CI result. A source-pinned GitHub Actions full suite workflow is staged on this review branch; status must be checked and raw preserved.
- Preserved intermediate **local** failures: SHA256SUMS paths included `./` and required normalization for ZIP member lookup; private fixture copy had a trailing newline and correctly failed Git-blob validation until exact Git bytes were restored locally. Preserved intermediate **remote** test-file mistake: a transient Library visibility error was accidentally committed as text, then restored at `eb5f968d3a40452736c3985320527028655b630b`; final test blob verified `5bd0e0468c96474d7fc43a00faaa8ccb8f0a4ce1`. No failed attempt is relabelled PASS.

## Continuation and gates

Next: verify GitHub CI exact-source focused/full results and artifact hashes; independently review paired input validator counterexamples; keep routehead train64 child separate; pursue substantive full-scope roadmap (JEF/C2/C3/B1/B2, STEP2, B3, Body-JEPA, Context OS, Dream/Sleep, Redmi). Do not train on either transfer64 or original96 evaluation rows.

**Unchanged:** `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `LP3_heldout=FAIL`, `jepa_weight=0`, `Age0=RECORD_ONLY`, `phone_measured=false`, `whole_system_complete=false`. Branch-scoped only; no AGI claim.
