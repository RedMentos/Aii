# Run155 first full-repository CI failure (preserved)

Workflow run 40162181739, job 121075857878 (2026-10-25T04:31Z), at head b3ecaa1cc777f31cbcd84854267fa78328dd6ec0. Focused test result **9 PASS, 1 ERROR**; privacy step skipped because test step failed.

Failure: `test_fake_native_artifact_fails_closed` expected ImportError/ModuleNotFoundError/ValueError but actual Run154 `load()` indexed a missing `report['schema']`, raising `KeyError: 'schema'`. The malformed synthetic artifact was correctly rejected, but the test's exception expectation was incomplete. Run155 corrected only the test expectation to include KeyError at commit c4d8b8ea910184272a91fbc5f7da9e033ad7a271. Run154 remains unchanged.

The failure is preserved and does not imply any native test or gate promotion. Exact job log is available at https://github.com/RedMentos/Aii/actions/runs/40162181739/job/121075857878. Recheck CI after the correction.
