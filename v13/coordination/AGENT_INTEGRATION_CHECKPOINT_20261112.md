# V13 agent integration evidence checkpoint — 2026-11-12

Release ancestry previously at `234319400b13cd4036464151ce4ce422b8fa8fd9`.

Boss-reviewed Core candidate originally in draft PR #1852:
- `v13/code/v13/android_outcomes.py`
- `v13/code/tests/test_android_outcomes.py`
- `.github/workflows/v13-android-outcomes-contract.yml`

The integrated merge commit `ac18bf5e819b9027d2fea07963d156fa23669d4e`
contains the full code candidate plus an adversarial sink-failure replay regression,
based on release ancestry. The preceding GitHub merge API request timed out
before its PR bookkeeping could be independently confirmed. Therefore do not
count PR #1858 as a verified closed/merged record solely from the client reply.

The explicit release checkpoint forces a new exact-HEAD push CI run for the
fixed Android release channel. Do not claim that the physical Redmi has
installed any of these bytes without a separate private device receipt.
The action outcome is intentionally `DRY_RUN_ONLY`,
`observed=False`, `SOFTWARE_SIMULATION`; it cannot count as a trusted T8
learning transition. Real Android companion transport remains unimplemented.
No model weights, permissions, private messages or device data are included.

All future agent deliverables should use the main-branch
`automation/README.md` review queue and the fixed
`v13/coordination/PHONE_RELEASE_TRAIN_2026-11-12.md` contract.
