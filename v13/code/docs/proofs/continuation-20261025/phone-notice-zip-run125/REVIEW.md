# Run125 independent review — startup notice and exact phone ZIP

Run124's preworker stop gate is preserved byte-for-byte. New UI-only helper consumes the **display list** `_startup_phone_halt` exactly once; it does not release, weaken or mutate persisted NOTAUS/STILLSTAND. Both plain and prompt-toolkit UI call it after assigning `r.notify`.

Test-first RED Actions 40148205182: one missing-notice FAIL, one missing-helper ERROR. Raw job log preserved. Post-fix Actions 40148272361: **30/30 PASS** on source and **30/30 PASS** on extracted exact-head phone ZIP; official privacy CLEAN. Phone ZIP 12,620,454 bytes SHA-256 `1287e280a6cfafc2a712250d9f3abdcb5f4f3a3a288b0c8ac6fff417138ed27d`; wrapper artifact ID 12582420001 SHA-256 `3a2faa74ac914655d47119cb436f0f1efc16b7a4205f68f8fea6c29292fefea0`.

Independent local verification: actual artifact downloaded via GitHub connector, both SHA-256 and CRC verified, required WP-UI1/Canon/preworker/notice files present, 30/30 Linux tests rerun on Python 3.13.5 PASS. A private Library copy of the wrapper exists at `/V13_Run125_20261025/V13_Phone_Run125_Artifact_Wrapper.zip`, size 12,620,608 bytes. Direct container_path Library uploads failed with `container_session_unavailable`; no rejected Drive retry.

Official Termux:Widget README (https://github.com/termux/termux-widget/blob/master/README.md) confirms `~/.shortcuts/` foreground scripts, `~/.shortcuts/tasks/` background scripts, and executable permissions; this is documentation consistency, not device execution proof.

No native models, no actual Android/Redmi test, no Body-JEPA or generated-answer utility proof. Canon blob unchanged; all negative gates retained. Next: bounded full-suite regression audit with pinned CPU-only torch.
