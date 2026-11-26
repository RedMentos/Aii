#include "native_receiver_kv_snapshot.hpp"
#include "ggml-backend.h"
#include "ggml.h"
#include "llama-context.h"
#include "llama-kv-cache.h"
#include "llama-memory-hybrid.h"
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <sstream>
#include <vector>
namespace v14 {
namespace {
struct CellRef { uint32_t index = 0; int32_t position = 0; };
struct GgmlContextGuard {
    ggml_context * value = nullptr;
    ~GgmlContextGuard() { if (value) ggml_free(value); }
};
struct RawSnapshot {
    int32_t layer_id = -1;
    uint32_t attention_layer_count = 0;
    std::vector<int32_t> positions;
    std::vector<int64_t> k_shape, v_shape;
    std::string k_type, v_type;
    std::vector<uint8_t> k_bytes, v_bytes;
    std::string position_sha256, k_sha256, v_sha256, combined_sha256;
    uint64_t bytes_read = 0;
};
void append_u32_le(std::vector<uint8_t> & out, uint32_t value) {
    out.push_back(static_cast<uint8_t>(value & 0xffu));
    out.push_back(static_cast<uint8_t>((value >> 8u) & 0xffu));
    out.push_back(static_cast<uint8_t>((value >> 16u) & 0xffu));
    out.push_back(static_cast<uint8_t>((value >> 24u) & 0xffu));
}
void append_i32_le(std::vector<uint8_t> & out, int32_t value) {
    append_u32_le(out, static_cast<uint32_t>(value));
}
void append_string(std::vector<uint8_t> & out, const std::string & value) {
    append_u32_le(out, static_cast<uint32_t>(value.size()));
    out.insert(out.end(), value.begin(), value.end());
}
std::vector<int64_t> tensor_shape(const ggml_tensor * tensor) {
    return {tensor->ne[0], tensor->ne[1], tensor->ne[2], tensor->ne[3]};
}
size_t transposed_v_head_base_offset(uint32_t cell, uint32_t stream, uint32_t head,
                                     size_t nb0, size_t nb1, size_t nb3) {
    return static_cast<size_t>(stream) * nb3 + static_cast<size_t>(head) * nb1
        + static_cast<size_t>(cell) * nb0;
}
bool capture_once(llama_context * context, int32_t sequence_id,
                  RawSnapshot & output, std::string & error_code) {
    if (!context || sequence_id != 0) { error_code = "SEQUENCE_NOT_SUPPORTED"; return false; }
    auto * hybrid = dynamic_cast<llama_memory_hybrid *>(context->get_memory());
    if (!hybrid) { error_code = "MEMORY_NOT_HYBRID"; return false; }
    auto * cache = hybrid->get_mem_attn();
    if (!cache) { error_code = "ATTENTION_CACHE_UNAVAILABLE"; return false; }
    std::vector<uint32_t> layer_ids = cache->get_layer_ids();
    if (layer_ids.empty()) { error_code = "NO_ATTENTION_LAYERS"; return false; }
    std::sort(layer_ids.begin(), layer_ids.end());
    layer_ids.erase(std::unique(layer_ids.begin(), layer_ids.end()), layer_ids.end());
    const uint32_t stream_count = cache->get_n_stream();
    const uint32_t stream_id = stream_count == 1 ? 0u : static_cast<uint32_t>(sequence_id);
    if (stream_count == 0 || stream_id >= stream_count) {
        error_code = "SEQUENCE_STREAM_UNAVAILABLE"; return false;
    }
    const auto & cells = cache->get_cells(sequence_id);
    std::vector<CellRef> active;
    active.reserve(cells.get_used());
    for (uint32_t index = 0; index < cells.size(); ++index) {
        if (cells.is_empty(index) || !cells.seq_has(index, sequence_id)) continue;
        const auto position = cells.pos_get(index);
        if (position < 0) { error_code = "NEGATIVE_ACTIVE_POSITION"; return false; }
        active.push_back({index, static_cast<int32_t>(position)});
    }
    std::sort(active.begin(), active.end(), [](const CellRef & a, const CellRef & b) {
        return a.position != b.position ? a.position < b.position : a.index < b.index;
    });
    if (active.empty()) { error_code = "NO_ACTIVE_SEQUENCE_CELLS"; return false; }
    for (size_t i = 1; i < active.size(); ++i) {
        if (active[i - 1].position == active[i].position) {
            error_code = "DUPLICATE_ACTIVE_POSITION"; return false;
        }
    }
    auto memory_context = cache->init_full();
    auto * kv_context = dynamic_cast<llama_kv_cache_context *>(memory_context.get());
    if (!kv_context || kv_context->get_status() != LLAMA_MEMORY_STATUS_SUCCESS) {
        error_code = "FULL_CACHE_VIEW_UNAVAILABLE"; return false;
    }
    ggml_init_params params{};
    params.mem_size = 1024 * 1024;
    params.mem_buffer = nullptr;
    params.no_alloc = true;
    GgmlContextGuard graph_context{ggml_init(params)};
    if (!graph_context.value) { error_code = "GGML_VIEW_CONTEXT_FAILED"; return false; }
    const int32_t layer_id = static_cast<int32_t>(layer_ids.front());
    ggml_tensor * k_view = kv_context->get_k(graph_context.value, layer_id);
    ggml_tensor * v_view = kv_context->get_v(graph_context.value, layer_id);
    if (!k_view || !v_view) { error_code = "KV_LAYER_VIEW_UNAVAILABLE"; return false; }
    context->synchronize();
    const uint64_t cache_size = cache->get_size();
    if (k_view->ne[2] != static_cast<int64_t>(cache_size) ||
        k_view->ne[3] <= static_cast<int64_t>(stream_id)) {
        error_code = "K_VIEW_GEOMETRY_UNSUPPORTED"; return false;
    }
    const size_t k_features = static_cast<size_t>(k_view->ne[0] * k_view->ne[1]);
    const size_t k_row_bytes = ggml_row_size(k_view->type, k_features);
    if (k_row_bytes == 0 || k_view->nb[2] != k_row_bytes) {
        error_code = "K_ROW_LAYOUT_UNSUPPORTED"; return false;
    }
    output.layer_id = layer_id;
    output.attention_layer_count = static_cast<uint32_t>(layer_ids.size());
    output.k_shape = tensor_shape(k_view);
    output.v_shape = tensor_shape(v_view);
    output.k_type = ggml_type_name(k_view->type) ? ggml_type_name(k_view->type) : "unknown";
    output.v_type = ggml_type_name(v_view->type) ? ggml_type_name(v_view->type) : "unknown";
    output.positions.clear(); output.k_bytes.clear(); output.v_bytes.clear();
    output.positions.reserve(active.size());
    output.k_bytes.reserve(active.size() * k_row_bytes);
    for (const auto & cell : active) {
        if (cell.index >= cache_size) { error_code = "K_CELL_OUT_OF_RANGE"; return false; }
        const size_t offset = static_cast<size_t>(cell.index) * k_view->nb[2]
            + static_cast<size_t>(stream_id) * k_view->nb[3];
        const size_t old_size = output.k_bytes.size();
        output.k_bytes.resize(old_size + k_row_bytes);
        ggml_backend_tensor_get(k_view, output.k_bytes.data() + old_size, offset, k_row_bytes);
        output.positions.push_back(cell.position);
    }
    const bool v_transposed = v_view->ne[0] == static_cast<int64_t>(cache_size);
    const size_t v_features = v_transposed
        ? static_cast<size_t>(v_view->ne[1] * v_view->ne[2])
        : static_cast<size_t>(v_view->ne[0] * v_view->ne[1]);
    if (v_view->ne[3] <= static_cast<int64_t>(stream_id) || v_features == 0) {
        error_code = "V_VIEW_GEOMETRY_UNSUPPORTED"; return false;
    }
    if (v_transposed) {
        const size_t type_size = ggml_type_size(v_view->type);
        const size_t block_size = ggml_blck_size(v_view->type);
        const size_t heads = static_cast<size_t>(v_view->ne[1]);
        const size_t head_dim = static_cast<size_t>(v_view->ne[2]);
        if (block_size != 1 || type_size == 0 || v_view->nb[0] != type_size) {
            error_code = "TRANSPOSED_V_CACHE_TYPE_UNSUPPORTED"; return false;
        }
        const size_t per_cell_bytes = v_features * type_size;
        output.v_bytes.reserve(active.size() * per_cell_bytes);
        for (const auto & cell : active) {
            if (cell.index >= cache_size) { error_code = "V_CELL_OUT_OF_RANGE"; return false; }
            const size_t old_size = output.v_bytes.size();
            output.v_bytes.resize(old_size + per_cell_bytes);
            for (uint32_t head = 0; head < heads; ++head) {
                const size_t offset = transposed_v_head_base_offset(
                    cell.index, stream_id, head, v_view->nb[0], v_view->nb[1], v_view->nb[3]);
                ggml_backend_tensor_get_2d(
                    v_view,
                    output.v_bytes.data() + old_size + static_cast<size_t>(head) * head_dim * type_size,
                    offset, type_size, head_dim, v_view->nb[2], type_size);
            }
        }
    } else {
        if (v_view->ne[2] != static_cast<int64_t>(cache_size)) {
            error_code = "V_TOKEN_AXIS_UNSUPPORTED"; return false;
        }
        const size_t v_row_bytes = ggml_row_size(v_view->type, v_features);
        if (v_row_bytes == 0 || v_view->nb[2] != v_row_bytes) {
            error_code = "V_ROW_LAYOUT_UNSUPPORTED"; return false;
        }
        output.v_bytes.reserve(active.size() * v_row_bytes);
        for (const auto & cell : active) {
            if (cell.index >= cache_size) { error_code = "V_CELL_OUT_OF_RANGE"; return false; }
            const size_t offset = static_cast<size_t>(cell.index) * v_view->nb[2]
                + static_cast<size_t>(stream_id) * v_view->nb[3];
            const size_t old_size = output.v_bytes.size();
            output.v_bytes.resize(old_size + v_row_bytes);
            ggml_backend_tensor_get(v_view, output.v_bytes.data() + old_size, offset, v_row_bytes);
        }
    }
    std::vector<uint8_t> position_bytes;
    position_bytes.reserve(output.positions.size() * sizeof(int32_t));
    for (const auto position : output.positions) append_i32_le(position_bytes, position);
    std::vector<uint8_t> combined;
    combined.reserve(sizeof(int32_t) * 3 + position_bytes.size()
        + output.k_bytes.size() + output.v_bytes.size() + 64);
    append_i32_le(combined, output.layer_id);
    append_i32_le(combined, sequence_id);
    append_u32_le(combined, static_cast<uint32_t>(output.positions.size()));
    append_string(combined, output.k_type);
    append_string(combined, output.v_type);
    combined.insert(combined.end(), position_bytes.begin(), position_bytes.end());
    combined.insert(combined.end(), output.k_bytes.begin(), output.k_bytes.end());
    combined.insert(combined.end(), output.v_bytes.begin(), output.v_bytes.end());
    output.position_sha256 = sha256_hex(position_bytes);
    output.k_sha256 = sha256_hex(output.k_bytes);
    output.v_sha256 = sha256_hex(output.v_bytes);
    output.combined_sha256 = sha256_hex(combined);
    output.bytes_read = static_cast<uint64_t>(output.k_bytes.size() + output.v_bytes.size());
    return true;
}
void write_int_array(std::ostringstream & out, const std::vector<int64_t> & values) {
    out << "[";
    for (size_t i = 0; i < values.size(); ++i) { if (i) out << ","; out << values[i]; }
    out << "]";
}
void write_position_array(std::ostringstream & out, const std::vector<int32_t> & values) {
    out << "[";
    for (size_t i = 0; i < values.size(); ++i) { if (i) out << ","; out << values[i]; }
    out << "]";
}
}  // namespace
bool capture_readonly_kv_snapshot(llama_context * context, int32_t sequence_id,
                                  NativeKvSnapshot & output, std::string & error_code) {
    const auto started = std::chrono::steady_clock::now();
    RawSnapshot first, second;
    if (!capture_once(context, sequence_id, first, error_code)) return false;
    if (!capture_once(context, sequence_id, second, error_code)) return false;
    if (first.layer_id != second.layer_id ||
        first.attention_layer_count != second.attention_layer_count ||
        first.positions != second.positions ||
        first.k_shape != second.k_shape || first.v_shape != second.v_shape ||
        first.k_type != second.k_type || first.v_type != second.v_type ||
        first.k_sha256 != second.k_sha256 || first.v_sha256 != second.v_sha256 ||
        first.combined_sha256 != second.combined_sha256) {
        error_code = "DOUBLE_READ_NOT_STABLE"; return false;
    }
    output.status = "READ_ONLY_SNAPSHOT";
    output.cache_kind = "LLAMA_MEMORY_HYBRID_ATTENTION";
    output.snapshot_scope = "ONE_ATTENTION_LAYER_ONE_SEQUENCE";
    output.sequence_id = sequence_id;
    output.layer_id = first.layer_id;
    output.attention_layer_count = first.attention_layer_count;
    output.active_cell_count = static_cast<uint32_t>(first.positions.size());
    output.position_ids = std::move(first.positions);
    output.k_shape = std::move(first.k_shape);
    output.v_shape = std::move(first.v_shape);
    output.k_type = std::move(first.k_type);
    output.v_type = std::move(first.v_type);
    output.position_sha256 = std::move(first.position_sha256);
    output.k_sha256 = std::move(first.k_sha256);
    output.v_sha256 = std::move(first.v_sha256);
    output.combined_sha256 = std::move(first.combined_sha256);
    output.stable_read_sha256 = second.combined_sha256;
    output.bytes_read_per_snapshot = first.bytes_read;
    output.double_read_bytes_read = first.bytes_read + second.bytes_read;
    output.duration_us = static_cast<uint64_t>(
        std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::steady_clock::now() - started).count());
    output.read_only = true;
    output.double_read_stable = true;
    output.raw_data_exported = false;
    output.recurrent_state_included = false;
    error_code.clear();
    return true;
}
std::string native_kv_snapshot_json(const NativeKvSnapshot & snapshot) {
    std::ostringstream out;
    out << "{"
        << "\"schema\":\"v14.native-receiver-kv-snapshot/1\""
        << ",\"status\":\"" << snapshot.status << "\""
        << ",\"cache_kind\":\"" << snapshot.cache_kind << "\""
        << ",\"snapshot_scope\":\"" << snapshot.snapshot_scope << "\""
        << ",\"sequence_id\":" << snapshot.sequence_id
        << ",\"layer_id\":" << snapshot.layer_id
        << ",\"attention_layer_count\":" << snapshot.attention_layer_count
        << ",\"active_cell_count\":" << snapshot.active_cell_count
        << ",\"position_ids\":";
    write_position_array(out, snapshot.position_ids);
    out << ",\"position_sha256\":\"" << snapshot.position_sha256 << "\""
        << ",\"k_type\":\"" << snapshot.k_type << "\""
        << ",\"v_type\":\"" << snapshot.v_type << "\""
        << ",\"k_shape\":";
    write_int_array(out, snapshot.k_shape);
    out << ",\"v_shape\":";
    write_int_array(out, snapshot.v_shape);
    out << ",\"k_sha256\":\"" << snapshot.k_sha256 << "\""
        << ",\"v_sha256\":\"" << snapshot.v_sha256 << "\""
        << ",\"combined_sha256\":\"" << snapshot.combined_sha256 << "\""
        << ",\"stable_read_sha256\":\"" << snapshot.stable_read_sha256 << "\""
        << ",\"bytes_read_per_snapshot\":" << snapshot.bytes_read_per_snapshot
        << ",\"double_read_bytes_read\":" << snapshot.double_read_bytes_read
        << ",\"duration_us\":" << snapshot.duration_us
        << ",\"read_only\":true"
        << ",\"double_read_stable\":true"
        << ",\"raw_data_exported\":false"
        << ",\"recurrent_state_included\":false"
        << "}";
    return out.str();
}
int native_kv_snapshot_selftest() {
    std::vector<uint8_t> bytes;
    append_i32_le(bytes, 0); append_i32_le(bytes, 1); append_i32_le(bytes, 2);
    if (sha256_hex(bytes) != "ad5dc1478de06a4c2728ea528bd9361a4b945e92a414bf4d180cedaaeaa5f4cc") return 1;
    if (transposed_v_head_base_offset(2, 1, 1, 2, 24, 96) != 124) return 2;
    if (transposed_v_head_base_offset(2, 1, 1, 2, 24, 96) + 8 != 132) return 3;
    return 0;
}
}  // namespace v14
