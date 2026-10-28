# Run11 F3 SelfState cross-session unfinished count — original RED (2026-10-28)

Prereg `777dfd5ba28bd9c25705aea1fa54a0ef99031a38`, test `daa8aa2b673ae99594bdd7b20e14a115f512160c`, workflow/source `ce590c468f1d0194f4dfe42e6cf6fda50a73165f` before any new SelfState implementation. Source World blob `7f9b266828deace320adce86304aa22fdb55de18` inherited from PR #863; its multi-action focused tests pass on this exact run.

[Linux software RED 40645249350](https://github.com/RedMentos/Aii/actions/runs/40645249350): 11 focused tests, **2 expected failures** — prior-session `DISPATCHED` and `OUTCOME_UNKNOWN` both incorrectly counted in current session. Nine other focused tests pass, including all four prior multi-action tests. BLOBS/INSTALL/COMPILE/PRIVACY/DIFF exit0, FOCUSED exit1, FULL SKIPPED_RED. Synthetic Runtime/SQLite only; no native/Redmi proof.

Raw artifact `12797238585`, ZIP SHA256 `f65557826513356bc623cc3c8edd28e20c71358dfb1a305bc548bdcf07ee62b3`, CRC and 16/16 SHA256SUMS verified. Private Library `/V13-Checkpoints/2026-10-28/Run11-SelfState-Session/SELFSTATE_SESSION_RED_40645249350_shaf6555782.zip` uploaded. Preserve this original failed attempt. Next patch: scope `unfinished_actions` count to current session by joining events. No gate promotion or production integration.
