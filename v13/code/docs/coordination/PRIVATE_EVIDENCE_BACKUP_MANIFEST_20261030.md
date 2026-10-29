# Private durable evidence backup manifest — 2026-10-30

The eight exact GitHub Actions RED/GREEN raw ZIP artifacts for review PRs #1175–#1178 and one unfiltered full-suite ZIP for PR #1179 were copied to the user's **private ChatGPT Library** folder `/V13/automation-evidence/20261030/`. This is **not** the rejected anyone-writable Drive destination; no public source, data or model artifacts were added to it.

Every upload succeeded, was independently listed from Library, then rematerialized **from Library** and compared byte-for-byte via SHA256 against the downloaded original GitHub artifact ZIP. **9/9 match**, ZIP CRC **9/9 clean**. The eight focused ZIPs have 18/18 internal `SHA256SUMS` each; the full-suite ZIP has 30/30. GitHub Actions artifacts have 30-day retention; the private Library copies preserve these raw files separately.

| Review | ZIP filename | SHA256 (remote Library re-read) |
| --- | --- | --- |
| 1175 RED | `github-actions-artifact-12941179909.zip` | `f1a365ef3a5234ca4a91c4c5afeb2de7599db1d3494aa68f66de3a99cfbaa073` |
| 1175 GREEN | `github-actions-artifact-12941668249.zip` | `2872a7e9909c2610677ac0f92f43db8f55ad5e3759a9c7eb67e01d5b257dfc12` |
| 1176 RED | `github-actions-artifact-12941778275.zip` | `7a37da224275a3779a999093b52fb2ab232079958a445ccd4e99d96fe006d4f1` |
| 1176 GREEN | `github-actions-artifact-12940939367.zip` | `73d6c2f87b06cabcfccfb634e4f66ea2d21d275edf271234306ce5cb5d9653fc` |
| 1177 RED | `github-actions-artifact-12941707780.zip` | `2be4336982a3b25719bca0bc84ca96205b9c2be6cc7894dde424423bc03c6ed7` |
| 1177 GREEN | `github-actions-artifact-12941529278.zip` | `0227a76a1fde31bf53fef4a2e9a50545c1a128f97a3b525861cf9645a80ecc69` |
| 1178 RED | `github-actions-artifact-12942113235.zip` | `0ad0148bfdc3ba63085db63b1784921946e5c98fbee180d8777939237dde65a1` |
| 1178 GREEN | `github-actions-artifact-12941947640.zip` | `af8e464a567f26cb3eb10ddafbac07ccc4128724f48a52ec3cb84c8f4c0fb45a` |
| 1179 unfiltered FULL RED (frozen Run34/Run37 only) | `github-actions-artifact-12942567969.zip` | `9052c4f4df15cd3cb45cdd578bf924361522aac59b8c07584d791c5a0ae44cd5` |

Original GitHub artifact IDs remain recorded in each package's `*_RESULT_20261030.md` and build-state delta. This public manifest exposes only generic names and digests, not private Library IDs or contents. The full unfiltered combined suite PR #1179 finished: 3372 tests, 2 preserved frozen Run34/Run37 source-preflight errors, 11 skips, no new errors. Its raw ZIP was uploaded to the same private folder and byte-verified. No source pin or negative gate was changed. No whole-system/Redmi/native/gate promotion.
