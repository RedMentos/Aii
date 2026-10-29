# V13 JEF cross-organ unfiltered software review — preregistration 2026-10-30

Base: PR #1168, verified checkpoint `44ccc360a1ddd0cb6168b6e7deb945b404392995`. Review-only CI package; no production/Canon source, registered cohort or model change. Ownership: new CI workflow, this preregistration and review delta only.

## Question
Do the new JEF operator current-chat guard and duplicate human-label receipts coexist with all other V13 modules without introducing a new software regression? Focused 19/19 and 24/24 tests already passed separately. They do not substitute for a full unfiltered replay.

## Frozen execution
- Ubuntu 24.04 isolated venv: NumPy 2.2.6, torch 2.5.1+cpu from the official CPU wheel index, Transformers 4.44.2, PEFT 0.13.2, psutil/PyYAML/Pillow/prompt-toolkit.
- `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py'`, **without exclusions, skip injection or waivers**.
- Existing frozen Run34/Run37 native source-preflight failures from historical `utility.py` identity are expected and must remain RED. Do not rewrite original historical evidence or promote gates. Any additional failure must be distinguished.
- Capture all original raw, exact commit, source blob hashes, dependency freeze, exit statuses, Canon SHA, privacy/diff check, internal SHA256SUMS. Upload even if RED. Check artifact CRC and hashes after remote save.
- No model downloads or actual native JEF/C2/Redmi execution. This is software-only cross-organ review.
