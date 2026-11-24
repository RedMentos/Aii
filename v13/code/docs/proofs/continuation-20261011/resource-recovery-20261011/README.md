# Native resource recovery after scratch loss

**Completed: RESTORED_EXACT_BINDING.** The launcher, all 19 shared-library filename/hash entries, all three model bytes and all model revisions exactly match the original preregistration. `llama-server --version` exits 0. No inference was run during recovery. The original native artifact binding therefore remains valid; any continuation still validates its own source/checkpoint/lifecycle binding.

The repository and all closed reports were recovered from verified GitHub commit `3d63ec8e8f5735f7a6c6a5675635ea115d51242c`. The model cache, upstream native source and native build were transient resources and had to be downloaded/rebuilt.

All three GGUF downloads use their original catalog URL, revision, byte size and SHA256; no replacement model is chosen. The b10964 source archive is checked against the original SHA256 before extraction. The existing memory hook patch is applied without modifying runtime or harness sources. Patched server.cpp, server-context.cpp and memory-hook header all match the original saved native build manifest.

The rebuild uses the original Release/CPU/OpenMP-off/native-off/CURL-off build flags and two compile jobs for the 8-GiB cgroup. CMake is separately installed under scratch (`4.4.4`). The final launcher and every shared-library byte hash must be compared with the old preregistration before a native proof can continue. A source-equivalent rebuild alone does not establish binary binding equality; any differences require a transparent new recovery binding before inference.

See `native-resource-recovery.json` for machine-readable current status. This recovery is neither a utility proof nor a Redmi measurement, and starts no inference itself. Historical failures and completed rows remain unchanged.

The build completed with exit 0. The cgroup recorded memory-pressure `max=1016`, `oom=0`, and `oom_kill=0`; pressure alone is not an OOM kill. Nonfatal precompiled-header warnings remain in the closed build log. Despite the header fallback, the resulting complete launcher/library map is byte-identical to the old artifact binding.
