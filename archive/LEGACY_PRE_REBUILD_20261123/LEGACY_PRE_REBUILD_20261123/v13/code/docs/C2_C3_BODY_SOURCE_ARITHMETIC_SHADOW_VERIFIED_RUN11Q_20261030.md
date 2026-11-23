# Run11Q original C2/C3/Body source-grounded arithmetic shadow audit — verified (2026-10-30)

Review-only child of PR #1245. Preregistration `b70574156cfb68839296c20429725fb3b77ff638` committed before implementation. Exact tested source `2406d355d4d2af5f2de3190b73d7a44edd58ec40`. Original Actions **41033010731 SUCCESS**, artifact **12966612981**, ZIP SHA256 **`76a6ad3e77062a60bfdc85ba4bbbf8afa9d5e35c3b00a4c9298a976f036a3d44`**, 4611 bytes, CRC clean, **19/19** inner SHA256SUMS independently verified, **8/8** stage exits zero, **11/11** adversarial software tests PASS, privacy CLEAN. Original raw was privately backed up at `/V13-Checkpoints/2026-10-30/Run11Q-C2C3-Arithmetic-Shadow/SOFTWARE_GREEN_41033010731_sha76A6AD.zip`, re-materialized, and SHA256 compared byte-identical.

**Historical input:** Original Linux-native C2/C3/Body Actions **40999648419**, artifact **12952434876**, exact ZIP SHA256 `df680697f65f9879b7817179b8d4a2d1f8625656579c68f03c0268d599f6d4c4`, CRC clean, 27/27 inner hashes, original HEAD `4f73e39db16d9ff4570dc6d3b4586160dc18d0a3`, original fixture SHA256 `74818535a13819a65d4d32801d704fecd7716ea99c112b33c3bca248f3442c36`. This is **posthoc** scoring of the exact existing output, not a new native run or preregistered utility cohort. The new scorer independently verifies the original ZIP/manifest/source and ignores untrusted score fields. It never alters source data, routing or answers.

**Source-grounded remaining-budget claims:**

| Fixture | Option | Correct source remainder | Original generated claim | Result |
| --- | --- | ---: | ---: | --- |
| Zephyr47 | Marigold | 96 | 191 | CONTRADICTS_SOURCE |
| Zephyr47 | Basalt | 24 | 263 | CONTRADICTS_SOURCE |
| Solstice47 | Kestrel | 132 | 132 | MATCH |
| Solstice47 | Linden | 27 | 127 | CONTRADICTS_SOURCE |
| Talon47 | Orion | 56 | 56 | MATCH |
| Talon47 | Willow | 24 | 124 | CONTRADICTS_SOURCE |

**Totals: 2/6 MATCH, 4/6 CONTRADICTS_SOURCE, 0 unscored/conflicting.** Not a model accuracy estimate or a comparative benefit: all original outputs were B1_DETAIL; native C2 invoked 3/3 but selected route **0/3**; C3 FINAL **0/3**. The four wrong numbers were explicit source contradictions, not just formatting mistakes. This supports the need for a source-grounded contradiction veto or uncertainty marker before promoting answer authority, but no live veto is enabled here.

**Preserved first RED:** Actions **41032861606 FAILURE**, ZIP SHA256 `fdefe4a4baae39718cb67560f1755cea85d6e57e9b64f8557f98f4e084787ea2`, 16/16 hashes, original unit test error caused by a shallow-copy synthetic fixture mutation shared across tests. Corrected only test fixture isolation, not scorer/runtime/original evidence. First RED privately backed up at `/V13-Checkpoints/2026-10-30/Run11Q-C2C3-Arithmetic-Shadow/SOFTWARE_RED_41032861606_shaFDEFE4.zip`, byte-reverified. New source script blob `d824690e942489b11c79c3aa68cd0f02e6176f06`; fixed test blob `54bba1955955e9d0bc31b8bb6104002eb67e99e5`. No production merge.

**Gates remain negative:** Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, runtime jepa_weight0, C2 native-selected route unproven on non-simple scaffolds, C3 FINAL unobserved in this cohort, Redmi UNMEASURED, V13 incomplete. Next substantive package: new disjoint preregistered paired C2/C3/Body utility experiment with C3-only, B1-only, B2-only, both, and same-Body-two-state controls, using this scorer only as a **frozen evaluation mechanism**, not as evidence of causal benefit by itself.
