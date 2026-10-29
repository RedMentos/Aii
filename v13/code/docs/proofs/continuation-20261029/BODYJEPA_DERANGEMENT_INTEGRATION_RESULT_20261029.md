# Body-JEPA changed-source existing torch/PEFT regression — observed result (2026-10-29)

- Review-only PR #1153, source candidate Git blob `fe912d908868d5e923297fa52b44e09f1e39bf1f`, Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.
- Separate preregistration `BODYJEPA_DERANGEMENT_INTEGRATION_PREREG_20261029.md`; workflow launched only after full PEFT suite `40960222503` completed, avoiding overlapping heavy model jobs.
- GitHub Actions `40961078579` exact HEAD `c5052795070ccf36b5273b4907562fd3220f51a0` **GREEN 25/25** existing and new tests: `tests.test_bodyjepa_derangement_bound_20261029`, `tests.test_body_jepa`, `tests.test_body_jepa_checkpoint_fit`, `tests.test_body_jepa_checkpoint`. No exclusions, no model download.
- Isolated imports confirmed `torch==2.5.1+cpu`, `transformers==4.44.2`, `peft==0.13.2`; `pip check` exit0. All 11 stages CANON/VENV/DEPS/TORCH/HF/PIP_CHECK/IMPORT/FOCUSED/COMPILE/PRIVACY/DIFF exit0.
- Original artifact ID `12934478924`, ZIP SHA256 `100b3fce6c83e78bb475b3a69765c4d3b9ed9f973d5697d5d8688500424673d5`, CRC clean, **24/24** internal hashes independently matched. Private Library backup `/V13-Checkpoints/2026-10-29/Run10-BodyJepaDerangement/v13-bj-integration-GREEN-40961078579.zip`, byte-exact readback verified.
- Earlier fail-first 4-test RED and corrected 4-test GREEN retained unchanged, with separate original raw ZIPs. The broader existing BJ1 test set now passes on the **changed** Body-JEPA source, not merely on the unpatched parent.

**Limit:** Tiny synthetic HF software-only. This is not deployed LFM2 Body-JEPA learning, retention gain, native training or Redmi. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, AG6 unapproved, V13 INCOMPLETE. Next work must pursue independent functional utility and genuine model evidence rather than promote these unit tests.
