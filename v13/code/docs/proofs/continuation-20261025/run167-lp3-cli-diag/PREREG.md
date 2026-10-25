# Run167 prereg — diagnose Run164 LP3 CLI rc=1 without waiving failures

Exact parent `02f417744aae245976add8a861bf3ab69f5830b0`. Owner new workflow and proof only; no frozen runtime/helper/model/registered cohort edits. Reuse exact Run164 reconstructed LP3 helper and source hash checks, Run147 artifact, pinned CPU-only dependencies, official privacy and serialized full-suite. In runner temp ONLY, patch one assertion in the reconstructed **test** file to include captured CLI stderr/stdout when `rc != 2`; assert exactly one source occurrence before patch and log pre/post Git blobs. No changed expected return code, no skipped test, no runtime helper modification. Run full 2358+ discovery once; preserve raw log even on FAIL. Use same `v13-native-c3-run131-serialized` group.

Known baseline: Run164 run `40164058854` 2358, 5 FAIL, 11 SKIP; second `40164344635` 2358, 4 FAIL, 11 SKIP. Three inherited CLI rc=1 vs expected 2 failures stable; synthetic live descendant cleanup FAIL stable. Sleep/Wake failure intermittent. No claim of kernel containment, native model proof or V13 completion.

Next after diagnostics: use actual stderr to isolate import/environment or CLI regression, fix in isolated candidate with tests; retain real cgroup kernel gate. If diagnostic CI unavailable, leave blocker open and continue independent V13 organs.
