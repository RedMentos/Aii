#!/usr/bin/env bash
# WP-S6 rest: native finetune tools that can train LFM2 (C3/B1). Isolated candidate around the unchanged
# build_native_finetune.sh (hash-bound in the tested-package manifests):
#   1. applies patches/ggml-lfm2-backward-b10964.patch once (SSM_CONV + CONCAT backward, contiguous TRANSPOSE gradient,
#      larger training graph budget, masked labels in llama_context::opt_epoch_iter, cross-entropy backward that is
#      exact for all-zero (masked) label rows);
#   2. builds native-select-finetune + llama-quantize via build_native_finetune.sh;
#   3. builds native-answer-finetune (answer-only loss, scripts/native_answer_finetune.cpp).
#   bash scripts/build_native_lfm2_finetune.sh <pristine llama.cpp-b10964 source dir> [jobs]
# Gradient check of the patch: configure with -DLLAMA_BUILD_TESTS=ON, then build/bin/test-backend-ops grad -o SSM_CONV
# (and -o CONCAT).
set -euo pipefail
SRC="$(cd "$1" && pwd)"; JOBS="${2:-2}"; HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! grep -q 'V13 WP-S6: y\[i,t,s\]' "$SRC/ggml/src/ggml.c"; then
  patch -d "$SRC" -p1 < "$HERE/patches/ggml-lfm2-backward-b10964.patch"
fi
bash "$HERE/build_native_finetune.sh" "$SRC" "$JOBS"
DST="$SRC/examples/v13-answer-finetune"
mkdir -p "$DST"; cp "$HERE/native_answer_finetune.cpp" "$DST/"
cat > "$DST/CMakeLists.txt" <<'EOF'
set(TARGET native-answer-finetune)
add_executable(${TARGET} native_answer_finetune.cpp)
install(TARGETS ${TARGET} RUNTIME)
target_link_libraries(${TARGET} PRIVATE llama-common llama ${CMAKE_THREAD_LIBS_INIT})
target_compile_features(${TARGET} PRIVATE cxx_std_17)
EOF
grep -q 'v13-answer-finetune' "$SRC/examples/CMakeLists.txt" || echo 'add_subdirectory(v13-answer-finetune)' >> "$SRC/examples/CMakeLists.txt"
cmake -S "$SRC" -B "$SRC/build" >/dev/null
cmake --build "$SRC/build" -j"$JOBS" --target native-answer-finetune
ls -la "$SRC/build/bin/native-answer-finetune"
