# V13 session continuation — SourceHandoff preflight hardening v6

- Tested in isolated staged Python 3.13 Linux source tree: **31 focused tests PASS** (9 sealed-streaming, 7 audit, 15 resume-guard). Logs + exact SHA-256 manifests in local `/V13/V13_WORK_REVIEW_20261012_v6.zip` (`c7146f62e0edfaf137247dc190e075353657e244b40802b305693c1f75776853`), mirrored to user's ChatGPT Library.
- Guard now rejects noncanonical row order (the frozen ablation produces a fixture-major/arm-minor prefix) and a supposedly `RECORDED` row missing FINAL native producer/consumer metrics, approved structural checks, oracle isolation or process reap. Failed rows remain preserved as diagnostic evidence.
- **No edits** to frozen `source_handoff_ablation.py`, original native model source or numerical preregistration. Guard is only a candidate; original 16-case inference not run here.
- GitHub read-back both new files and SHA-bound content. PR #2 unmerged, authority branch unchanged. All initial STEP2/B3 failures preserved.
- Follow-up reviewer: check historical protocol compatibility, restore actual archived 12-part evidence independently; run full suite before integrating any candidate. Continue original 16-case native handoff and Dream2/NumPy experiments under serial model budget.
