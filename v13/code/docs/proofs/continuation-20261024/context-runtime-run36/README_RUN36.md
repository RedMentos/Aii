# V13 Run36 — ContextOS pinned-history ACTIVE budget fail-closed candidate

Parent: PR #71 Run35 `9e1119162b3a8bf2f99341de7cb1d8afd1bcae5d`; PR #68 Run32 isolated guard. This is a source-bound **review candidate**, not a production edit or a claim of full Runtime proof. File ownership: only `v13/code/docs/proofs/continuation-20261024/context-runtime-run36/`.

## Verified source-path defect

Frozen `v13/code/v13/context_os.py` Git blob `028376012e328624fb527a927bb0e2a1071a86a0` has a budget-pressure loop over `(unpinned, [pinned older turns])`, allowing pinned older turns to become COMPRESSED or POINTER. The actual `v13/code/v13/runtime.py` Git blob `a691d27bd0772a4fa1f03d57ec90663237bf6825` catches **all** ContextOS exceptions and continues with the unplanned legacy messages, including if ContextOS was ACTIVE. This is a static source finding; the exact excerpt's synthetic execution reproduced the pinned turn changing to POINTER under pressure and the legacy exception fallback. No full runtime reproduction yet.

## Candidate

`context_pin_runtime_patch.py` refuses source blob mismatches, symlinks and existing output destinations; emits patched full copies only to a new output folder, never mutates production files. It excludes pinned/restored turns from compression/pointer candidates, measures actual planned message characters, and raises `ContextBudgetExceeded` for ACTIVE overflow. The Runtime patch preserves the SHADOW fallback but re-raises on ACTIVE or unreadable mode state. It does not change any context knob, user rule, Age right, model or source. The exact historical `ContextOS` state, SourceRefs and canonical Exact Recall gate remain untouched.

## Reproduce and integrate safely

With a complete verified checkout at the exact pinned Git blob identities:

```
python scripts/context_pin_runtime_patch.py --context v13/code/v13/context_os.py --runtime v13/code/v13/runtime.py --output /tmp/v13-context-pin-run36-candidate
python -m unittest discover -s tests -v
```

Run `python -m unittest v13/code/tests/test_context_os.py` from the proper project root (or the repository's documented invocation), the full original suite, official privacy scanner, and a real Runtime ACTIVE overflow test **before** integration. Re-check the current heads; if source blobs changed, review/rebase rather than overriding newer work. The script is not an auto-integrator.

## Evidence and limits

`python -m unittest discover -s tests -v`: **10/10 software/synthetic PASS**; `compileall` PASS. Original fixture behavior and patched behavior compared; an initial malformed fixture and a too-specific RED expectation failed and were preserved. Tests run the exact budget-loop anchors but NOT the full original ContextOS or native KV/model. Actual source-bound patch application, full repo tests, official privacy scanner, native model, Redmi and §8.4 Exact Recall proof remain **NOT RUN**.

Original gates unchanged: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Z6a FAIL; Z8 FAIL; full V13 INCOMPLETE.
