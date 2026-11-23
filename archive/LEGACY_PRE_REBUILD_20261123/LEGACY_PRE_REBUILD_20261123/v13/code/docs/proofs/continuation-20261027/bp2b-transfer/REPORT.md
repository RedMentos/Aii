# WP-BP2b transfer source-only checkpoint · 2026-10-27

Owner: automation11 BP2b transfer, PR #706 review-only child of PR #705 exact `592e8975e52e3765e5acd893cd56aa69e936473f`. Prereg `6cdc0caec3a1ddc73a59b5c63290c6168eeecf00` committed before the fixed new transfer data. Source commit `9e7c5c3f027ad9b6ef9807ba817169d8619aa3f1`, script blob `853660938b55ac1d8ac3a022c942cd99f4fad7e2`.

GitHub Actions `40501836243` exact head `faf4896d5a9542c1d25da48a1f9e6eda57eb0d46`: 14/14 software PASS (6 transfer + 8 locality), three `--prepare-only` seed runs 41/42/43 PASS, compile0, privacy CLEAN, raw artifact `12733496282`, original ZIP SHA256 `d2c96330be15593f8b0c1d10a0665fa7cedde5922c866bfbf7f48516cc13bf35` (8871 bytes), CRC PASS, 20 members, private Library backup `/V13-Checkpoints/2026-10-27/BP2b-Transfer-Cohort/` re-materialized byte-identical. Original failed BP2b grammar counterexamples from parent PR #705 retained.

Cohort source SHA256 `7af8de5f8c052c2e008f517cc3b287e7d39d803d30c8efbaea1d9b2dacc08155`; heldout 24×2 candidate SHA256 `2d974299db28854f6565bf9f00896d408c5ee000530e845fd6b6f37bc12ab113`. Each of seeds 41/42/43 selects 16 facts and 32 source-disjoint heldout prompts. Model-facing files include only `case_id` and `prompt`, scoring keys separate; no native predictions or training were produced.

Seed | Train SHA256 | Model-facing SHA256 | Scoring-only SHA256
--- | --- | --- | ---
41 | `2519682a8d27e63419c30a226815d2bf2896c76ec6848d9ccd09a24c2bfe7f49` | `853c3abb8e703362e31a5936d06bb7af8ca53ace1c10cc11d349c2b97068ce87` | `95983d3f3c4d7b27c0461b99d115f9b8a8a48ee73ee58cf4a23e19b178005576`
42 | `068e9db4320578d56a705e2671afcfe005eced4c0dbac690a2996e9c0d591dad` | `06b0ff607ffb69b0b8200307ca88d2550b5b4ad084da81a99f1d325965e68542` | `57c825470de5d9da95156a9b3b5ee4bf3d13fa43b1ab6876f10f5a02c9641d51`
43 | `43bf3d7db1b33176586b041bf81bb86ca28aec00aa6f9bbc6253f6a2864d60d2` | `cba5c121f6cce69ece59c7edb73feb59b20aa1ed756a69bd09c68d70410b0e44` | `d4b2e5eeff47ce1aab71ad3dd9898bcfbb6e80bc9c388306e7acd1d7c94758ea`

Next: build a source-bound **native training/evaluation runner** in a new child review branch, enforcing source/master/tokenizer/adapter/seed hashes, 4 preregistered arms and strict model-facing vs scoring-only separation. Verify current heavy-job owner before activation; no model downloaded in this package. A single native result cannot promote Age, STEP2, B3, Body-JEPA or whole-system gates. Future Q4/Redmi evidence separate.

Exact software replay: `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_transfer_cohort tests.test_bp2b_locality_anchors`; fixture: `PYTHONPATH=v13/code python v13/code/scripts/bp2b_transfer_cohort.py --out /tmp/bp2b-transfer --seed 41 --prepare-only`.
