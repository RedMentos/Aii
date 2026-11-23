# Native resources after second automated workspace cleanup

This recovery is separate from the original 2026-10-11 resource proof. The original preregistration and result files are preserved. The three pinned GGUF files, b10964 source archive, compiler version, CMake 4.4.4, source patch, Release CPU build flags and two build jobs are reused.

The driver runs no inference. Its launcher and adjacent runtime library hashes must all match the original frozen installed binding before the original capture or source-handoff protocol may resume. Model installation metadata is recreated using the unchanged ModelManager, with deep hash verification. Needle and physical Redmi evidence are not included.

Reproduction: run `PATH=/root/.local/bin:$PATH python3 -u recovery-driver.py` from the app directory after installing `cmake==4.4.4`. Paths in the driver record this recovered workspace. The model cache and native build remain outside the repository.

`native-resource-recovery.json` records the actual outcome; `native-build.log` contains the raw CMake/build output. Recovery does not establish a learned utility result or a canonical gate pass.

The separate `native-runner-b10964-linux-x86_64.closed.tar.gz` artifact contains only the eight unique ELF files, their relative library/launcher symlinks and configuration manifests (26 archive entries, 6,453,915 compressed bytes). It excludes GGUF files, source and build objects. `runner-bundle-inventory.json` binds its SHA, and `runner-bundle-restore-qa.json` verifies a fresh extraction, all 24 manifest paths, relative aliases and an actual successful `--version` invocation. `full-preregistered-binding-preflight.json` compares the unchanged harness binding to the original preregistration, including all 121 source files and all native artifacts.
