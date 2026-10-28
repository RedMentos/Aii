# Run86 prereg — actual `python -m v13` process-level Age0 CLI (2026-10-28)

Owner GPT-6 scheduled continuation. Review-only child of Run85 #992 head `d013330454fd95d58491a21eb85c813df0698370`, parent CI pending at preregistration. This is the **actual Linux Python command-line entrypoint**, not an in-process Operator call; no installed models, no native inference, no Redmi.

## Frozen test plan

1. Use `subprocess.run([sys.executable,'-m','v13','--home',fresh_tmp,'doctor'])` with `PYTHONPATH` bound to this source tree, `HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE/NO_MODEL_DOWNLOADS=1`, timeout 30 seconds. Exit code 0 means diagnostic data integrity only. Parse stdout JSON, require Age0 RECORD_ONLY, missing language/body/gist/needle, `canonical_architecture_complete=false`, B3 latents OFF, body training UNAVAILABLE, tools OFF, and empty data-integrity errors.
2. Run `chat --plain` with exactly one piped operator command per process (to avoid multi-line paste coalescing): `:status\n`, `:help\n`, `:shutdown\n`. All must exit within 20 seconds with return code 0, display the expected operator content and never attempt native model download or generation.
3. Run `doctor` again on same home and verify unchanged Age0/negative gates and persistent state. No model artifacts installed and no network calls; no false success claim.
4. CI pinned source/entrypoint/tests, focused subprocess test + Run85 doctor and Run82 lifecycle tests, full software suite, privacy and closed raw hashes. Preserve any RED. No source code changes or user data.
5. This is executable Linux CLI evidence only, not C3/B1/B2 native model output, semantic quality, sustained Redmi resources, STEP2/B3/Body-JEPA/LP3 or full blueprint completion.

If Run85 parent RED, child cannot integrate. Do not retune any prior native cohort or promote a gate from this software smoke.
