# Core phone installed-runtime health — 2026-11-12 15:04 Europe/Berlin

- Owner: Core & Harness. Package: CORE-PHONE-HEALTH-20261112.
- Base release branch: `gpt6/v13-private-remote-bridge-20261111`, SHA `3058619a23e39da0e9e5e28dfe69b14e0cec7dbe`.
- Independent branch: `gpt6/v13-core-phone-health-20261112-1504`, checkpoint `41383692000c0ae7a83eca57ff565a455a43dc70`.
- Draft review PR: #1847. **NOT RELEASED**, not integrated into phone branch.
- Changed: `v13/code/v13/phone_release_health.py`, `v13/code/tests/test_phone_release_health.py`, `.github/workflows/v13-core-phone-health.yml`.
- New executable operator diagnostic: `PYTHONPATH=v13/code python -m v13.phone_release_health`. Reads the private installed runtime marker, hashes the actual launcher, checks immutable staged required files and rejects paths outside build root. It does not inspect model/SQLite/chat bytes or grant capabilities.
- Offline tests authored: ready, launcher tamper and missing module, marker path escape, unsafe/symlink marker. **CI NOT VERIFIED** at checkpoint (workflow query returned zero PR-triggered runs); no local exact-checkout test because direct git fetch DNS failed. No Android evidence.
- Other owners: Boss release branch integration; QA diagnostic replay; Perception audio; JEPA training. Do not overwrite their modules.
- Concurrent Core #1845 repairs source-to-installed required-file integrity in `runtime_deploy.py`; this diagnostic currently checks only required-file presence and launcher hash, **not** source hashes. Boss should review the two as complementary and avoid claiming full snapshot attestation.
- Negative gates unchanged: STEP2, B3, Android native control, full voice, B1/B2/C3 weight learning and AGI acceptance remain open.
- Exact next commands after checkout: `PYTHONPATH=v13/code python -m unittest discover -s v13/code/tests -p test_phone_release_health.py -v`; `PYTHONPATH=v13/code python -m v13.phone_release_health --help`; review CI for PR #1847, then inspect #1845 and integrate only after tests and review.
- No private data, token or device identifier was uploaded. GitHub readback confirmed `phone_release_health.py` blob SHA `274149da6d8a07872634c7ba6a99b2ef91ba3a50`.
