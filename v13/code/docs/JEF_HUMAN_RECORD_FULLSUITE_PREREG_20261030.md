# JEF human-record precedence: unfiltered full-software cross-organ replay prereg (2026-10-30)

Review-only child of #1185 at verified `5f341acaba4ff37289cde0753448c6b3829f27ec`. No runtime source changes in this package. Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7` must remain unchanged.

Goal: run `python -m unittest discover -s tests -p 'test_*.py'` unfiltered in an isolated pinned CPU Torch/Transformers/PEFT environment after the JEF human-record fix. Capture all original raw logs, stage exit codes, dependency versions, source hashes, privacy and diff, even if the suite is RED. **No test filtering, no skipped frozen negative gate, no source/model hash changes.**

Expected known historical source-bound failures: Run34 and Run37 original native preflight tests compare against a frozen earlier utility source blob and correctly report `native_source_or_catalog_changed` on the current hardened utility source. These failures must remain RED on the current branch. An isolated exact-historical worktree replay exists separately in #1180 and must not be misrepresented as current-source GREEN.

Check whether there are **additional** failures introduced by #1185. A CI job is GREEN only if every unfiltered test and stage is GREEN; otherwise record the exact failing tests and classify known frozen historical vs new. Preserve software/native/Redmi evidence distinctions. No Age/STEP2/B3/Body-JEPA/whole-system promotion.

Owner: automation. This package owns only its prereg, workflow, and result handoff; does not edit another owner's source.
