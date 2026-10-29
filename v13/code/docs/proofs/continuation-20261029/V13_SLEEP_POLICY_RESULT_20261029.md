# Sleep/Dream finite replay-mix policy — verified software result (2026-10-29)

Owner: GPT-6; draft review PR #1086, parent #1085 exact `46d0b7e665bb88c3a6e76c51a6ec201010704d1c`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## RED-first and source

- Prospective prereg commit `e9d61703f1f443449bcd39749c2d3bb0f68e4768` before implementation.
- Original RED run [40866677801](https://github.com/RedMentos/Aii/actions/runs/40866677801): 39 focused tests, 6 failures +3 errors on nonfinite/bool/bad-shape inputs, all other source/privacy stages 0. Original ZIP SHA256 `2f065672901a2ce197ca88860bf425325e9f3661452ab37baf5dd70f577d8f1d`, 21/21 internal hashes, CRC clean, private backup byte-verified at `/V13/RawEvidence/2026-10-29/V13_SLEEP_MIX_RED_40866677801_sha2f065672.zip`.
- Production source change is only `v13/code/v13/sleep.py` Git blob `3f6c91b1ab4ac02624a86049373957ff7bd93fd2` (11-line delta). Test blob `da3e97bfd9ca8808ec2208d21ac6c1b76236fa84`. Strict finite/nonnegative weights and finite positive total, strict int hours; valid replay semantics untouched.
- Workflow dependency addendum documents independent Context OS missing-torch full-suite RED; isolated CPU torch/transformers pins match established V13 full-suite workflow.

## GREEN

- Exact source-pinned [Actions 40866865992](https://github.com/RedMentos/Aii/actions/runs/40866865992), head `3225756b6ad41222ea58623c148778d168a07735`, completed **SUCCESS**.
- **39/39 focused tests PASS**, **3130 full software tests PASS, 11 skipped**. All 9 stage exits `SOURCE,VENV,DEPS,PIP_CHECK,FOCUSED,FULL,COMPILE,PRIVACY,DIFF` = 0. Privacy CLEAN. No model download/native execution.
- Original ZIP artifact `12894432063`, SHA256 `adcc91b3e9658962115309bd8fc47a13a86e8a8088db962e9279cba91bbee458`, CRC clean, 21/21 internal SHA256SUMS. Private backup `/V13/RawEvidence/2026-10-29/V13_SLEEP_MIX_GREEN_40866865992_shaadcc91b3.zip` independently rematerialized and byte-equal.

## Limits and next

This is **Sleep policy software integrity only**; no native replay improvement, learned JEPA, Redmi proof or production merge. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; Redmi unmeasured; V13 INCOMPLETE. Next exact command: `gh run view 40866812715 --repo RedMentos/Aii --json status,conclusion,headSha` and `gh run view 40866860307 --repo RedMentos/Aii --json status,conclusion,headSha`; verify original Context/Self artifacts, then integrated cross-organ #1087 and pursue substantive P2 receiver/Redmi prerequisites without gate promotion. Remaining platform budget UNKNOWN.
