# Run494 — independent fail-closed HF custom-license metadata correction

Date 2026-10-26. Base Run492 PR #490 at `122e1ed62ba2b04841ae567051754da399282c7e`; source/model/runner/fixture pins unchanged. Original Run492 live metadata Actions 40295185211 RED, raw artifact 12637094802, SHA256 `cc8efd8bb9d2055591ae4d316a546d2d4fd696244c626cef13624d84fd940cea`: ValueError MODEL_LICENSE_METADATA_CHANGED in first model. Original failure retained.

Primary-source public model card of LiquidAI/LFM2.5-1.2B-Instruct-GGUF exposes `license: other`, `license_name: lfm1.0`, `license_link: LICENSE`. Run492 only checks `cardData.license` or `tags: license:...`, so it fails to recognize the named custom license. The correct behavior is not to substitute a different license or claim acceptance: require the exact `other` + `lfm1.0` + `LICENSE` triple for LiquidAI's pinned models, or an explicitly equivalent exact direct `lfm1.0` declaration, while rejecting mismatched, missing, conflicting or altered license fields. Apache-2.0 stays exact. Preserve `license_accepted_by_user=None`.

Test preregistration: adversarial card with only `license: other` and no name fails; wrong license_name/link fails; conflicting tags fail; exact named LFM license passes; Apache-2.0 passes and mismatches fail. Run live pinned HF metadata preflight without model bytes, original runner or native execution. Raw Actions logs and SHA256 manifest retained on both RED/GREEN. No gate promotion: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi unmeasured.

If live metadata still fails on SHA/LFS/size/revision/gating, preserve failure and do not silently change registered pins. This is a separate review branch; do not edit Run492 owner branch.
