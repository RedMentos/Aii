# Android/Termux atomic Action-JEPA restore prerequisite — 2026-10-12

Isolated work branch `assistant/evidence-streaming-20261012`; no production source or Android device touched.

## Primary-source research
- Android Bionic status: `renameat2` is available since Android R / API level 30: https://android.googlesource.com/platform/bionic/+/refs/heads/ndk-release-r21/docs/status.md
- Android NDK/Bionic stdio declaration explicitly exposes `RENAME_NOREPLACE=1` and `renameat2` introduced at API 30: https://android.git.googlesource.com/platform/prebuilts/runtime/+/cdbb81ce1dabd0c8a876572fefaee4f410b24efe/mainline/runtime/sdk/android/riscv64/include/bionic/libc/include/stdio.h
- Scope: Android 13 corresponds to an Android API level newer than 30, so Bionic provides the symbol in principle. This does **not** prove the user's device filesystem accepts no-replace atomic directory renames, nor that Termux permissions/internal mount behave as expected.

## Implemented zero-weight phone prerequisite probe
`scripts/action_jepa_delta_atomic_publish_candidate.py` includes a `--probe-directory` CLI path. It creates and deletes only a private temporary subtree on the selected filesystem, checks that an atomic directory rename succeeds, then that rename to an existing occupied directory is refused without overwriting either directory. The temporary subtree is removed afterwards.

Example once the reviewed source is available under Termux on the phone:

```sh
python scripts/action_jepa_delta_atomic_publish_candidate.py --probe-directory "$HOME/v13"
```

A successful probe reports `ATOMIC_NOREPLACE_FILESYSTEM_PROBE_PASS`, with `canonical_gate_pass=false`. It is **not** native JEPA/model utility proof. The execution done in this session was Linux Python 3.13, not Android/Redmi.

## Testing, proof and handoff
- **68/68** focused CPU/Linux unit tests pass in the isolated staged tree and the older V13 October 11 snapshot with candidates overlaid, including three new filesystem probe tests and nine previous atomic destination tests.
- Local CRC and per-file SHA checked `V13_WORK_REVIEW_20261012_v12.zip`, SHA256 `4d14a86e3a3136aa8197cdddba91033161c6acc8bf8599b61f9a262e3911ea2e`, mirrored in ChatGPT Library under `/V13/`.
- The existing 1875 native rows, actual NPZ restore, 16-case source handoff, seeds 13/21/34, Dream2 2/15 and Redmi quality gates still have not been run by this isolated candidate. Do not promote STEP2 UTILITY_FAIL or B3 L1 FAIL.

This is not a request for immediate user action. Work can decide when the one-off filesystem probe belongs in the original phone acceptance sequence.
