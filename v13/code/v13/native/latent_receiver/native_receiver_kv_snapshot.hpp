#pragma once
#include <cstdint>
#include <string>
#include <vector>
struct llama_context;
namespace v14 {
std::string sha256_hex(const std::vector<uint8_t> & input);
struct NativeKvSnapshot {
    std::string status = "READ_ONLY_SNAPSHOT";
    std::string cache_kind = "LLAMA_MEMORY_HYBRID_ATTENTION";
    std::string snapshot_scope = "ONE_ATTENTION_LAYER_ONE_SEQUENCE";
    int32_t sequence_id = 0;
    int32_t layer_id = -1;
    uint32_t attention_layer_count = 0;
    uint32_t active_cell_count = 0;
    std::vector<int32_t> position_ids;
    std::vector<int64_t> k_shape;
    std::vector<int64_t> v_shape;
    std::string k_type;
    std::string v_type;
    std::string position_sha256;
    std::string k_sha256;
    std::string v_sha256;
    std::string combined_sha256;
    std::string stable_read_sha256;
    uint64_t bytes_read_per_snapshot = 0;
    uint64_t double_read_bytes_read = 0;
    uint64_t duration_us = 0;
    bool read_only = true;
    bool double_read_stable = false;
    bool raw_data_exported = false;
    bool recurrent_state_included = false;
};
bool capture_readonly_kv_snapshot(llama_context * context, int32_t sequence_id,
                                  NativeKvSnapshot & output, std::string & error_code);
std::string native_kv_snapshot_json(const NativeKvSnapshot & snapshot);
int native_kv_snapshot_selftest();
}  // namespace v14
