# QA handoff — JEPA source-lifecycle pin repair (2026-11-22)

## State

The QA branch has been merged with the latest JEPA Run 14 base commit `50e3c8dfe2e270c0e7f6024f2fec64a1970a1f9b` using a two-parent merge commit. The QA PR remains DRAFT / NOT_RELEASED. No Redmi deployment or native learning acceptance is claimed.

## Reproduced exact-head failure

On the previous exact QA head `71df3dc86017bd05b5f56f4ee06f00461801a594`, the Python 3.13/3.14 optimizer-resume and staged/integrated jobs failed at two downstream pins:
- Termux recovery expected training-builder SHA-256 `27fe2305...`, actual `6a72d48d...`.
- Integrated stage expected Termux wrapper SHA-256 `c6c6bed3...`, actual `d6ca01fe...`.
The staged runtime failed with `integrated builder hash mismatch`. The CI logs, not a local run, supplied these exact observations.

## Corrected chain on the QA branch

- `memory.py` SHA-256: `33377446f8dca709c0d829764dac6e1d4f1ca92729b955d8a8ad983a16bb1701`.
- Source-lifecycle composer SHA-256: `99230a8b63ec61083a58826c9a7499266cddfaa34088d9c76ea4f28b3a0aaaf6`.
- Memory/world builder SHA-256: `0e6c6d2d344df6288869976ff1047bd25d5b3dcd63224d371b36135a6493caec`.
- Feedback builder SHA-256: `0e73bdff980e7c90786560dc9875029acc74c48d13e7182294ea829d8f8675ba`.
- Context-recall builder SHA-256: `d7246b8d273d191d9faa56d8aa76eda8f06376b0c211ff71ce02d75bd2021b64`.
- World-JEPA training-resume builder SHA-256: `6a72d48dab40cbd8b4e8e7012b95fccdbf1f6755cb055bacf2c02fb0d3805ba4`.
- Termux recovery-12 Git blob SHA-1: `51b7555063c0a0584cce60e896555d4031956b25`; its World-JEPA builder pin now matches the SHA-256 above.
- Termux recovery-21 SHA-256: `ebd02940bdd3170d911467b6e2e8aea6d8971b5be6629cb3079eddf29bdc4ea9`; its recovery-12 Git blob pin now matches `51b755...`.
- Integrated stage SHA-256: `7cde60a058218f5890a39d5acec9cbb7d20d391e6b4106dd943763b789be3f5e`; its Termux recovery-21 pin now matches `ebd029...`.
- Runtime deployer `STAGER_SHA256` now matches the integrated-stage SHA-256 above.
- The regression checks the full source/builder chain and now also checks `runtime_deploy.py` → `stage_integrated_candidate.py`, so a later deployer mismatch is detected rather than discovered only at runtime.

## Verification boundary

- GitHub CI on the previous exact head: FAIL, with the two mismatches above.
- Current exact-head CI: PENDING until the workflows triggered by the final chain/test update complete; do not infer success from the hash readback.
- LOCAL_LINUX full Aii test suite: BLOCKED / NOT_RUN because this execution environment has no Aii checkout and GitHub DNS/network is unavailable.
- Termux/Redmi: REDMI_UNVERIFIED. No private device command, chat, native probe, update request, or device mutation was issued.
- No model, weight, SQLite, chat, permission, or installed-app state was changed.

## Independent blockers retained

The separate Boss-owned Record-Only controller/source pin and fair-budget composition failures are not silently changed by this QA PR. JEPA's SleepRuntime postcommit error and actual source-disjoint held-out receiver utility also remain separate acceptance requirements. Even a green staged test proves synthetic composition only, not Redmi performance, correct chat, native B1/B2 offers, or trained body weights.

## Next action

Review exact current-head Python 3.13/3.14 optimizer-resume and staged/integrated CI. If any failure remains, fix only the measured chain edge and rerun. Keep PR DRAFT until the shared matrix and independent review pass; after integration, rerun JEPA on the resulting exact base.
