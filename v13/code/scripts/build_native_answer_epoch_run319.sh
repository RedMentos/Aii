#!/usr/bin/env bash
# Run319: isolated native answer-finetune epoch checkpoint candidate.
# Prerequisite: exact pinned llama.cpp b10964 source tarball, verified externally.
# No production source/model/seed changes, no weight activation.
set -euo pipefail
if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "usage: bash scripts/build_native_answer_epoch_run319.sh <pristine-llama-b10964-source> <fresh-candidate-dir> [jobs]" >&2
  exit 2
fi
SRC="$(cd "$1" && pwd)"
CAND="$2"
JOBS="${3:-2}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$(cd "$HERE/.." && pwd)"
test ! -e "$SRC/examples/v13-answer-epoch-checkpoint-run319" || {
  echo "refusing existing candidate target" >&2; exit 3;
}
python3 "$HERE/prepare_native_answer_epoch_run319.py" \
  --source "$HERE/native_answer_finetune.cpp" \
  --patch "$HERE/patches/native-answer-epoch-checkpoint-run319.patch" \
  --out-dir "$CAND"
bash "$HERE/build_native_lfm2_finetune.sh" "$SRC" "$JOBS"
DST="$SRC/examples/v13-answer-epoch-checkpoint-run319"
mkdir "$DST"
cp "$CAND/scripts/native_answer_finetune.cpp" "$DST/native_answer_epoch_run319.cpp"
cat > "$DST/CMakeLists.txt" <<'EOF'
set(TARGET native-answer-epoch-checkpoint-run319)
add_executable(${TARGET} native_answer_epoch_run319.cpp)
install(TARGETS ${TARGET} RUNTIME)
target_link_libraries(${TARGET} PRIVATE llama-common llama ${CMAKE_THREAD_LIBS_INIT})
target_compile_features(${TARGET} PRIVATE cxx_std_17)
EOF
grep -q 'v13-answer-epoch-checkpoint-run319' "$SRC/examples/CMakeLists.txt" || \
  echo 'add_subdirectory(v13-answer-epoch-checkpoint-run319)' >> "$SRC/examples/CMakeLists.txt"
cmake -S "$SRC" -B "$SRC/build" -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_SERVER=OFF -DCMAKE_BUILD_TYPE=Release >/dev/null
cmake --build "$SRC/build" -j"$JOBS" --target native-answer-epoch-checkpoint-run319
test -x "$SRC/build/bin/native-answer-epoch-checkpoint-run319"
sha256sum "$SRC/build/bin/native-answer-epoch-checkpoint-run319"
echo "RUN319_NATIVE_COMPILE_PASS (NO MODEL TRAINING)"
