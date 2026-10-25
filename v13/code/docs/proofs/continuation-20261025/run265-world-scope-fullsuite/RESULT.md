# Run265 exact full-suite result after synthetic WorldModel scope repair (2026-10-25)

- Exact tested head `bff28504ffc682a3f63a2e4165d0547f6ce3d539` on PR265, base PR264 `1336793237f295092701b9ce8fd895d7300557d6`.
- GitHub Actions run https://github.com/RedMentos/Aii/actions/runs/40186067607, full-suite job `121147115611`, privacy job `121147070241`.
- **2672 tests, 0 FAIL, 0 ERROR, 14 skipped**, 188.158 seconds; actual suite exit code 0, official privacy **CLEAN**.
- Closed raw artifact `12595618982`, ZIP SHA256 `2662d99487b686706dfed280d9bd8adfdc3cd462239175e9c76adb7c46f9c7c7`.
- Prior PR260 exact full-suite **2669 tests, 2 FAIL, 14 skipped** remains preserved in run 40185499205, artifact 12595902858 SHA256 `1959b681a2da917cfb0085400903da55e51c2b02ffd3ef0ab0a50bb4d97fb927`. Run264 restored synthetic-only ablation compatibility; source-bound production WorldModel guard unchanged.
- Classification: GitHub Linux software/synthetic full suite, NOT native inference, NOT Redmi, NOT JEPA training, NOT STEP2 utility. A green suite does not erase Run261's separately preregistered **3 RED terminal-action tests** or their actual failure evidence.
- Next: integrate Run266 reviewed terminal-status candidate under PR259 owner only after independent review; then rerun full suite on reconciled exact source. Run267 native G13 longrun is a separate serialized Linux experiment. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE.
