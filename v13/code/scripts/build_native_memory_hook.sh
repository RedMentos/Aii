#!/usr/bin/env bash
# Build scripts/native_memory_hook.cpp against a built llama.cpp tree (see build_native_finetune.sh for the source).
#   bash scripts/build_native_memory_hook.sh <llama.cpp-source-dir-with-build>
set -euo pipefail
SRC="$(cd "$1" && pwd)"; HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; B="$SRC/build/bin"
[[ -f "$B/libllama.so" ]] || cmake --build "$SRC/build" -j2 --target llama
${CXX:-g++} -O2 -std=c++17 "$HERE/native_memory_hook.cpp" -I"$SRC/include" -I"$SRC/ggml/include" -L"$B" -lllama -lggml -lggml-base -Wl,-rpath,"$B" -o "$B/native-memory-hook"
ls -la "$B/native-memory-hook"
