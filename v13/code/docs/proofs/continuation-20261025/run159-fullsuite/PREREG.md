# Run159 preregistered current-chain full-suite audit

Base: exact Run157 head `c282a881205bd1a14268297eded3c8a642e53bca`. Owner Run159 only new CI workflow/proof. Frozen Runtime and Canon, Run152/156/157, all other organs and negative gates remain untouched.

Plan: use GitHub Actions Ubuntu CPU-only, pinned isolated `numpy==2.3.5`, `prompt-toolkit==3.0.52`, `torch==2.9.1+cpu`; offline model flags; extract hash-checked existing LP3 helper into a temp directory only (do not modify repo); execute `python -m compileall -q v13 tests` and full `python -m unittest discover -s tests -p test_*.py -v`. Preserve raw log on failures; no fake skipped tests or gate promotions. Enforce exit status, official public repo privacy CLEAN.

The full suite is software/CPU, not a new native model, JEPA learning, Redmi or user acceptance. Concurrency uses existing serialized group `v13-native-c3-run131-serialized` and cancel-in-progress false. Stop on actual failure and retain evidence; continue independent packages without overlapping heavy jobs.
