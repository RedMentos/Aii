# Body training-port artifact race review — 2026-11-09

Status: **source-bound review candidate**, child of the other workstream's
[#1630](https://github.com/RedMentos/Aii/pull/1630), exact head
`f9002cc3826bec2a2a68b9b636a746b33273b96e`. The owner branch and its files are
not overwritten. This package does not train a Body or grant update authority.

## Independent finding

The #1630 diff and ten original tests were reviewed; its dedicated Actions
checks [42544010205](https://github.com/RedMentos/Aii/actions/runs/42544010205)
and [42544005207](https://github.com/RedMentos/Aii/actions/runs/42544005207)
reported success, and the source privacy scan was CLEAN. Its static symlink,
directory and symlinked-parent checks work for the covered cases. A new
deterministic counterexample replaces a previously checked master artifact
with a symlink just before the path-based hash. If the replacement has the
expected bytes, the original reports `PORT_BOUND_PROOF_REQUIRED` and
`port_bound=True` while the path is now a symlink. `update_authority` remains
zero; this is a false **binding diagnostic**, not evidence of training.

## Candidate and verification

`body_port_openat_candidate.py` opens the trusted home directory and walks
artifact/descriptor components relative to already opened directory handles,
using no-follow and nonblocking flags where supported. It hashes an open regular
file descriptor, compares file identity before/after reading, and reopens the
path to detect replacement during the inspection. It rejects duplicate-key or
oversized descriptors, FIFOs, symlinked components, traversal and malformed
parameter IDs. Runner execute mode comes from the inspected descriptor, not a
later unbound pathname lookup. Absence of required OS primitives fails closed.
It checks the exact #1630 `body_training.py` hash and has zero update authority.

`body_port_openat_integration_candidate.py` checks the source hashes and
changes only the diagnostic import in an isolated copy. The capability-profile
test uses the real `native_capability_profile` path and injects a deterministic
swap; the port is rejected and training capability stays `UNAVAILABLE/NONE`.

`PYTHONPATH=.:tests:scripts ... -m pytest -q tests/test_body_training_port.py tests/test_body_port_openat_candidate_20261109.py tests/test_body_port_openat_integration_20261109.py`: **23 passed**; the integration wrapper separately runs **22 passed** in its disposable copy. Tests include the parent counterexample, regular artifacts, file and directory replacement, in-place changes, descriptor replacement, symlink/FIFO, malformed inputs and the FP32 exception. They use temporary files, not real weights or native training.

The complete regular test directory on the exact #1630 parent was run in a
separate checkout with tracked `v13/code` and pinned CPU dependencies:
`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=.:tests:scripts OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 timeout 1200 /tmp/v13-online-review-venv/bin/python -m pytest -q tests`.
Result: **3 failed, 5,391 passed, 51 skipped, 94 errors, 3,022 subtests
passed**, 407.59 s, exit 1; local raw log SHA-256
`3ef8b7c0f08443c270adaf57c65da961ef6f9b1529f966effee5c9190333f816`.
Two failures and the 94 errors require unavailable original native ZIPs. The
third failure used a tracked historical file outside sparse `v13/code`; after
adding `v13/bench-results/ag6-live-20261010`, that individual test passed.
The original RED full-suite result remains unchanged and no raw-log backup is
claimed. The corresponding #1619 run has the **same 94 error test IDs**, the
same 3 failed test IDs, and 52 additional failures, many triggered by changed
frozen runtime hashes. This comparison does not by itself classify every one
of those 52 failures.

The returned path is not a durable file handle. A later consumer that reopens
it can still race after inspection; safe future training requires a bound open
handle or an equally strong revalidation protocol at the actual point of use.
The checks are sequential rather than an atomic multi-file snapshot, and Linux
software tests do not establish Android/Redmi support, resource use or model
utility. Historical STEP2, B3, JEPA and Age gates are unchanged.

Other independent review branches: #1631 covers local online-learning gates and
checkpoint integrity; #1632 binds explicit user feedback to the same world
action without claiming semantic gradients. They are not integrated here.
