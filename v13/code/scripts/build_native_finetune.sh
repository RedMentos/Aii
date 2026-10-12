#!/usr/bin/env bash
# Build V13's native selective finetune tool (scripts/native_select_finetune.cpp) inside a llama.cpp source tree.
# Works on Linux and Termux (pkg install cmake clang). CPU only: ggml-opt training needs no extra backend.
#   bash scripts/build_native_finetune.sh <llama.cpp-source-dir> [jobs]
# Source: the pinned b10964 tarball (specs/models.json runner.source_url) or the vendor/llama.cpp tree of the
# llama-cpp-python sdist on PyPI (used in the cloud, where GitHub source downloads are blocked).
set -euo pipefail
SRC="$(cd "$1" && pwd)"; JOBS="${2:-2}"; HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DST="$SRC/examples/v13-select-finetune"
mkdir -p "$DST"; cp "$HERE/native_select_finetune.cpp" "$DST/"
cat > "$DST/CMakeLists.txt" <<'EOF'
set(TARGET native-select-finetune)
add_executable(${TARGET} native_select_finetune.cpp)
install(TARGETS ${TARGET} RUNTIME)
target_link_libraries(${TARGET} PRIVATE llama-common llama ${CMAKE_THREAD_LIBS_INIT})
target_compile_features(${TARGET} PRIVATE cxx_std_17)
EOF
grep -q 'v13-select-finetune' "$SRC/examples/CMakeLists.txt" || echo 'add_subdirectory(v13-select-finetune)' >> "$SRC/examples/CMakeLists.txt"
cmake -S "$SRC" -B "$SRC/build" -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF -DCMAKE_BUILD_TYPE=Release >/dev/null
cmake --build "$SRC/build" -j"$JOBS" --target native-select-finetune llama-quantize
ls -la "$SRC/build/bin/native-select-finetune" "$SRC/build/bin/llama-quantize"
