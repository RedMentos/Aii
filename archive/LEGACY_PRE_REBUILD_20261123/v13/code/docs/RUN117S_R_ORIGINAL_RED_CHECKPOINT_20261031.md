# Run117S-R original adversarial RED — preserved before fix

- Exact frozen parent: Run117S #1499 at `dc0851db19a9872d580460dd67e650d247b7b6f2`.
- Preregistration committed `1b94928dcb36d867c3f239f9d753d7b20ca70cea` before tests.
- Adversarial tests commit `edb14b1fa37afc441fc0febd52cf21b09561e145`; original Actions HEAD `bbc744407dd03ec0a3d1ba3b674521dcc0b9495d`.
- GitHub Actions run **41228679323**, original terminal **FAILURE** (expected scientific RED): **4/4 new adversarial tests fail** because `select` incorrectly returns `SHADOW_SALIENT_B2_EXCERPT_VERIFIED` after tampering with prior USER message, prior event authority, prior hypothesis, or prior hypothesis authority. Original **11/11 inherited Run117S tests PASS**. Dependencies, compile, privacy CLEAN, git diff --check all exit 0.
- Original artifact ID **13052741730**, ZIP SHA256 `acdf28b066eae811d5d1ff175168758a86ba484a7f5b37c1aa10811294166f5c`, CRC PASS, **16/16** SHA256SUMS entries checked against actual ZIP bytes. Private byte copy at `/V13-Checkpoints/2026-10-31/Run117S-R-Prior-Binding/run117s-r-prior-binding-red-bbc74440.zip`, size 4108.
- No native inference; real SQLite + synthetic Body only; no output, tools, learning or gate promotion. All original STEP2/B3/JEPA/age/Redmi/whole-system negative gates remain. This RED is never overwritten or reclassified as GREEN.

Next: minimal source/hypothesis binding patch in isolated selector and rerun the exact four adversarial + eleven inherited tests under Actions, preserving a new original GREEN/RED artifact independently. No change to frozen seed1061 or model hashes.
