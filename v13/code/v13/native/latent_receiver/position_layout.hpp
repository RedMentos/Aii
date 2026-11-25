#pragma once

#include <cstddef>
#include <cstdlib>
#include <limits>
#include <vector>

#include <llama.h>

namespace v14 {

// llama.cpp's pinned M-RoPE/IMRoPE embedding-batch path reads four position
// sections (section-major, each of n_tokens entries). llama_batch_init()
// allocates only n_tokens positions, so callers must expand this buffer before
// llama_decode(). See ggml-org/llama.cpp#28963.
inline std::size_t positions_per_embedding(enum llama_rope_type rope_type) noexcept {
    return (rope_type == LLAMA_ROPE_TYPE_MROPE || rope_type == LLAMA_ROPE_TYPE_IMROPE) ? 4u : 1u;
}

inline bool prepare_embedding_positions(
        struct llama_batch & batch,
        enum llama_rope_type rope_type,
        int rows,
        const std::vector<int> & positions) {
    if (rows < 1 || positions.size() != static_cast<std::size_t>(rows) || batch.pos == nullptr) {
        return false;
    }

    const std::size_t row_count = static_cast<std::size_t>(rows);
    const std::size_t sections = positions_per_embedding(rope_type);
    const std::size_t maximum = std::numeric_limits<std::size_t>::max();
    if (row_count > maximum / sections) return false;
    const std::size_t total_positions = row_count * sections;
    if (total_positions > maximum / sizeof(llama_pos)) return false;

    for (int position : positions) {
        if (position < 0 || static_cast<unsigned long long>(position) >
                static_cast<unsigned long long>(std::numeric_limits<llama_pos>::max())) {
            return false;
        }
    }

    // llama_batch_init() in the pinned revision uses malloc(); realloc keeps
    // llama_batch_free() ownership intact and preserves the original pointer
    // if allocation fails.
    auto * expanded = static_cast<llama_pos *>(
        std::realloc(batch.pos, total_positions * sizeof(llama_pos)));
    if (expanded == nullptr) return false;
    batch.pos = expanded;

    for (std::size_t section = 0; section < sections; ++section) {
        for (int row = 0; row < rows; ++row) {
            batch.pos[section * row_count + static_cast<std::size_t>(row)] =
                static_cast<llama_pos>(positions[static_cast<std::size_t>(row)]);
        }
    }
    return true;
}

}  // namespace v14
