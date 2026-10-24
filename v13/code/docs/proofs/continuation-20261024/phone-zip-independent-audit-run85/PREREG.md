# Run85 prereg — independent source ZIP archive verifier

2026-10-24. Base Run84 PR117 `1e8109fdf0b1cdac2d0fc5b148c2764269882b70`.
Owner: `.github/workflows/v13-focused-proof.yml` independent verification step and new Run85 evidence only; no source packager or runtime modifications.

Run83/84 packager validates its own ZIP; independently verify the same produced ZIP using the existing, separate `scripts.phone_release_audit_candidate.verify_archive` function **before extraction or upload**. This verifier rejects duplicate entries, path traversal, symlinks/nonregular members, mismatched manifest membership, duplicate JSON keys, invalid SHA-256, altered bytes and CRC failure. It must return a nonempty manifest with >=100 source files and SHA-256 equal to the packager's own printed source ZIP digest. This is a read-only archive check; do not invoke `phone_release_audit_candidate.audit` full 260-module discovery, because that could trigger native jobs without resource/owner preflight.

Retain existing 377+ Linux CI, privacy scan, 71 extracted ZIP tests, Runtime source-ref restart and pinned artifact upload. Preserve failed raw logs and exact artifact metadata. Evidence remains Linux software/ZIP only, not Redmi, native model, STEP2/B3/JEPA utility or full V13 completion.
