#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>

#ifndef V14_LLAMA_REVISION
#define V14_LLAMA_REVISION "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"
#endif

#ifdef V14_WITH_LLAMA
#include <llama.h>
#include <ggml.h>
#include <ggml-backend.h>
#include "llama-model.h"
#endif

namespace v14 {
constexpr int kMaxRows = 64;
constexpr int kMaxDim = 8192;
constexpr int kMaxPosition = 131072;
constexpr const char * kPositionMode = "ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL";
constexpr std::size_t kMaxElements = 262144;
constexpr int kMaxTokenRows = 32;
constexpr std::size_t kMaxTokenRowElements = 262144;
constexpr double kEffectEpsilon = 1.0e-7;

bool valid_batch(int rows, int dim, const std::vector<float> & values) {
    if (rows < 1 || rows > kMaxRows || dim < 1 || dim > kMaxDim) return false;
    if (static_cast<std::size_t>(rows) * static_cast<std::size_t>(dim) > kMaxElements) return false;
    if (values.size() != static_cast<std::size_t>(rows) * static_cast<std::size_t>(dim)) return false;
    for (float value : values) {
        if (!std::isfinite(value) || std::abs(value) > 1.0e6f) return false;
    }
    return true;
}

bool valid_positions(int rows, const std::vector<int> & positions, int context_limit) {
    if (rows < 1 || rows > kMaxRows || positions.size() != static_cast<std::size_t>(rows)) return false;
    if (context_limit < rows) return false;
    int previous = -1;
    for (int row = 0; row < rows; ++row) {
        const int position = positions[static_cast<std::size_t>(row)];
        if (position < 0 || position >= context_limit || position >= kMaxPosition || position <= previous || position != row) return false;
        previous = position;
    }
    return true;
}

bool checked_row_slice(int token_id, std::int64_t vocab, std::size_t stride,
                       std::size_t row_bytes, std::size_t tensor_bytes,
                       std::size_t & offset) {
    if (token_id < 0 || vocab < 1 || token_id >= vocab || stride == 0 ||
        row_bytes == 0 || row_bytes > stride) return false;
    const std::size_t id = static_cast<std::size_t>(token_id);
    if (id > std::numeric_limits<std::size_t>::max() / stride) return false;
    offset = id * stride;
    return offset <= tensor_bytes && row_bytes <= tensor_bytes - offset;
}

bool parse_token_ids(const std::string & raw, std::vector<int> & ids) {
    if (raw.empty()) return false;
    std::stringstream stream(raw);
    std::string token;
    while (std::getline(stream, token, ',')) {
        if (token.empty() || ids.size() >= static_cast<std::size_t>(kMaxTokenRows)) return false;
        char * end = nullptr;
        const long value = std::strtol(token.c_str(), &end, 10);
        if (end == token.c_str() || *end != '\\0' || value < 0 ||
            value > std::numeric_limits<int>::max()) return false;
        const int token_id = static_cast<int>(value);
        if (std::find(ids.begin(), ids.end(), token_id) != ids.end()) return false;
        ids.push_back(token_id);
    }
    return !ids.empty();
}

std::vector<float> zero_control(std::size_t size) {
    return std::vector<float>(size, 0.0f);
}

std::vector<float> shuffle_control(const std::vector<float> & input, int rows, int dim) {
    std::vector<float> output(input.size(), 0.0f);
    if (rows < 1 || dim < 1 || input.size() != static_cast<std::size_t>(rows) * static_cast<std::size_t>(dim)) {
        return output;
    }
    if (dim > 1) {
        for (int row = 0; row < rows; ++row) {
            const std::size_t base = static_cast<std::size_t>(row) * dim;
            for (int col = 0; col < dim; ++col) {
                output[base + col] = input[base + ((col + 1) % dim)];
            }
        }
    } else if (rows > 1) {
        for (int row = 0; row < rows; ++row) {
            output[static_cast<std::size_t>(row)] = input[static_cast<std::size_t>((row + 1) % rows)];
        }
    } else {
        output = input;
    }
    return output;
}

std::vector<float> reverse_rows(const std::vector<float> & input, int rows, int dim) {
    std::vector<float> output(input.size(), 0.0f);
    if (rows < 1 || dim < 1 || input.size() != static_cast<std::size_t>(rows) * static_cast<std::size_t>(dim)) return output;
    for (int row = 0; row < rows; ++row) {
        const std::size_t source = static_cast<std::size_t>(rows - 1 - row) * dim;
        const std::size_t target = static_cast<std::size_t>(row) * dim;
        std::copy_n(input.data() + source, dim, output.data() + target);
    }
    return output;
}

double l2_norm(const std::vector<float> & values) {
    long double sum = 0.0L;
    for (float value : values) sum += static_cast<long double>(value) * value;
    return std::sqrt(static_cast<double>(sum));
}

double rms_delta(const std::vector<float> & a, const std::vector<float> & b) {
    if (a.empty() || a.size() != b.size()) return std::numeric_limits<double>::quiet_NaN();
    long double sum = 0.0L;
    for (std::size_t i = 0; i < a.size(); ++i) {
        const long double d = static_cast<long double>(a[i]) - b[i];
        sum += d * d;
    }
    return std::sqrt(static_cast<double>(sum / a.size()));
}

double cosine(const std::vector<float> & a, const std::vector<float> & b) {
    if (a.empty() || a.size() != b.size()) return std::numeric_limits<double>::quiet_NaN();
    long double dot = 0.0L, aa = 0.0L, bb = 0.0L;
    for (std::size_t i = 0; i < a.size(); ++i) {
        dot += static_cast<long double>(a[i]) * b[i];
        aa += static_cast<long double>(a[i]) * a[i];
        bb += static_cast<long double>(b[i]) * b[i];
    }
    if (aa <= 0.0L || bb <= 0.0L) return std::numeric_limits<double>::quiet_NaN();
    return static_cast<double>(dot / std::sqrt(aa * bb));
}

bool all_finite(const std::vector<float> & values) {
    return std::all_of(values.begin(), values.end(), [](float value) { return std::isfinite(value); });
}

std::string number(double value) {
    if (!std::isfinite(value)) return "null";
    std::ostringstream out;
    out << std::setprecision(10) << value;
    return out.str();
}

std::string json_escape(const std::string & value) {
    std::string out;
    out.reserve(value.size() + 8);
    for (unsigned char ch : value) {
        if (ch == '"' || ch == '\\') {
            out.push_back('\\');
            out.push_back(static_cast<char>(ch));
        } else if (ch < 0x20) {
            out.push_back(' ');
        } else {
            out.push_back(static_cast<char>(ch));
        }
    }
    return out;
}

std::string positions_json(const std::vector<int> & positions) {
    std::ostringstream out;
    out << "[";
    for (std::size_t i = 0; i < positions.size(); ++i) {
        if (i) out << ",";
        out << positions[i];
    }
    out << "]";
    return out.str();
}

bool parse_positions(const std::string & raw, int rows, std::vector<int> & positions) {
    std::stringstream stream(raw);
    std::string token;
    while (std::getline(stream, token, ',')) {
        if (token.empty()) return false;
        char * end = nullptr;
        const long value = std::strtol(token.c_str(), &end, 10);
        if (end == token.c_str() || *end != '\0' || value < 0 || value >= kMaxPosition) return false;
        positions.push_back(static_cast<int>(value));
    }
    return valid_positions(rows, positions, kMaxPosition);
}

int selftest() {
    const std::vector<float> input{1.0f, 2.0f, 3.0f, 4.0f};
    if (!valid_batch(2, 2, input)) return 1;
    if (valid_batch(0, 2, input)) return 2;
    if (valid_batch(2, 0, input)) return 3;
    if (valid_batch(2, 3, input)) return 4;
    if (valid_batch(kMaxRows + 1, 2, std::vector<float>((kMaxRows + 1) * 2, 1.0f))) return 5;
    auto bad = input;
    bad[0] = std::numeric_limits<float>::quiet_NaN();
    if (valid_batch(2, 2, bad)) return 6;
    bad = input;
    bad[0] = std::numeric_limits<float>::infinity();
    if (valid_batch(2, 2, bad)) return 7;
    const auto zeros = zero_control(input.size());
    if (rms_delta(input, zeros) <= 0.0) return 8;
    const auto shuffled = shuffle_control(input, 2, 2);
    if (shuffled == input) return 9;
    if (std::abs(cosine(input, input) - 1.0) > 1.0e-12) return 10;
    if (std::isfinite(cosine(input, zeros))) return 11; // zero-vector cosine must be undefined
    if (!all_finite(shuffled)) return 12;
    if (!valid_positions(2, std::vector<int>{0, 1}, 64)) return 13;
    if (valid_positions(2, std::vector<int>{1, 0}, 64)) return 14;
    if (valid_positions(2, std::vector<int>{0, 0}, 64)) return 15;
    if (valid_positions(2, std::vector<int>{0, 64}, 64)) return 16;
    if (reverse_rows(input, 2, 2) == input) return 17;
    std::size_t row_offset = 0;
    if (!checked_row_slice(2, 10, 64, 48, 640, row_offset) || row_offset != 128) return 18;
    if (checked_row_slice(-1, 10, 64, 48, 640, row_offset)) return 19;
    if (checked_row_slice(10, 10, 64, 48, 640, row_offset)) return 20;
    if (checked_row_slice(1, 10, 32, 33, 640, row_offset)) return 21;
    if (checked_row_slice(9, 10, 64, 49, 600, row_offset)) return 22;
    if (checked_row_slice(2147483647, 2147483647, std::numeric_limits<std::size_t>::max(),
                          1, std::numeric_limits<std::size_t>::max(), row_offset)) return 23;
    std::vector<int> token_ids;
    if (!parse_token_ids("0,12,4095", token_ids) || token_ids.size() != 3 ||
        token_ids[0] != 0 || token_ids[1] != 12 || token_ids[2] != 4095) return 24;
    token_ids.clear();
    if (parse_token_ids("1,1", token_ids)) return 25;
    token_ids.clear();
    if (parse_token_ids("-1", token_ids)) return 26;
    std::cout << "PASS\n";
    return 0;
}
}  // namespace v14

#ifdef V14_WITH_LLAMA
namespace {
struct BackendGuard {
    BackendGuard() { llama_backend_init(); }
    ~BackendGuard() { llama_backend_free(); }
};
struct ModelGuard {
    llama_model * value = nullptr;
    ~ModelGuard() { if (value) llama_model_free(value); }
};
struct ContextGuard {
    llama_context * value = nullptr;
    ~ContextGuard() { if (value) llama_free(value); }
};
struct BatchGuard {
    llama_batch value{};
    bool active = false;
    ~BatchGuard() { if (active) llama_batch_free(value); }
};

bool decode_token_row(const ggml_tensor * tensor, int token_id,
                      std::vector<float> & output, std::size_t & row_bytes,
                      std::size_t & offset) {
    if (!tensor) return false;
    const std::int64_t dim = tensor->ne[0];
    const std::int64_t vocab = tensor->ne[1];
    if (dim < 1 || dim > v14::kMaxDim || vocab < 1 ||
        tensor->ne[2] != 1 || tensor->ne[3] != 1) return false;
    row_bytes = ggml_row_size(tensor->type, dim);
    if (row_bytes == 0 || tensor->nb[1] < row_bytes ||
        !v14::checked_row_slice(token_id, vocab, tensor->nb[1], row_bytes,
                                ggml_nbytes(tensor), offset)) return false;

    // Read only the requested token row. Never call llama_model_get_tok_embd(),
    // which allocates and copies the complete vocabulary x embedding matrix.
    std::vector<std::uint8_t> raw(row_bytes);
    ggml_backend_tensor_get(tensor, raw.data(), offset, row_bytes);
    output.assign(static_cast<std::size_t>(dim), 0.0f);
    if (tensor->type == GGML_TYPE_F32) {
        if (row_bytes != static_cast<std::size_t>(dim) * sizeof(float)) return false;
        std::memcpy(output.data(), raw.data(), row_bytes);
    } else if (tensor->type == GGML_TYPE_F16) {
        if (row_bytes != static_cast<std::size_t>(dim) * sizeof(ggml_fp16_t)) return false;
        ggml_fp16_to_fp32_row(reinterpret_cast<const ggml_fp16_t *>(raw.data()),
                              output.data(), dim);
    } else if (tensor->type == GGML_TYPE_BF16) {
        if (row_bytes != static_cast<std::size_t>(dim) * sizeof(ggml_bf16_t)) return false;
        ggml_bf16_to_fp32_row(reinterpret_cast<const ggml_bf16_t *>(raw.data()),
                              output.data(), dim);
    } else if (ggml_is_quantized(tensor->type)) {
        const ggml_type_traits * traits = ggml_get_type_traits(tensor->type);
        if (!traits || !traits->to_float || traits->blck_size < 1 ||
            dim % traits->blck_size != 0) return false;
        traits->to_float(raw.data(), output.data(), dim);
    } else {
        return false;
    }
    return v14::all_finite(output);
}

int run_token_rows(const std::string & model_path, const std::vector<int> & token_ids) {
    if (std::string(V14_LLAMA_REVISION) != "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4" ||
        token_ids.empty() || token_ids.size() > static_cast<std::size_t>(v14::kMaxTokenRows)) {
        std::cerr << "unsupported pinned revision or token row count\\n";
        return 2;
    }
    BackendGuard backend;
    ModelGuard model;
    llama_model_params model_params = llama_model_default_params();
    model_params.n_gpu_layers = 0;
    model_params.load_mode = LLAMA_LOAD_MODE_MMAP;
    model.value = llama_model_load_from_file(model_path.c_str(), model_params);
    if (!model.value) {
        std::cerr << "model load failed\\n";
        return 3;
    }
    const llama_model * loaded = model.value;
    const ggml_tensor * tensor = loaded->tok_embd;
    const std::int64_t vocab = static_cast<std::int64_t>(loaded->vocab.n_tokens());
    const std::int64_t dim = tensor ? tensor->ne[0] : 0;
    if (!tensor || vocab < 1 || tensor->ne[1] != vocab || dim < 1 ||
        dim > v14::kMaxDim ||
        static_cast<std::size_t>(dim) * token_ids.size() > v14::kMaxTokenRowElements) {
        std::cerr << "receiver input token embedding tensor shape is unsupported\\n";
        return 4;
    }
    const std::size_t row_bytes = ggml_row_size(tensor->type, dim);
    if (row_bytes == 0 || tensor->nb[1] < row_bytes) {
        std::cerr << "receiver input token embedding row layout is unsupported\\n";
        return 4;
    }
    std::vector<std::vector<float>> rows;
    rows.reserve(token_ids.size());
    for (int token_id : token_ids) {
        std::vector<float> values;
        std::size_t actual_row_bytes = 0, offset = 0;
        if (!decode_token_row(tensor, token_id, values, actual_row_bytes, offset) ||
            actual_row_bytes != row_bytes) {
            std::cerr << "requested receiver token row could not be read safely\\n";
            return 5;
        }
        rows.push_back(std::move(values));
    }

    const char * type_name = ggml_type_name(tensor->type);
    std::cout << "{\\\"schema\\\":\\\"v14.native-token-rows/1\\\",\\\"runner_revision\\\":\\\""
              << V14_LLAMA_REVISION << "\\\",\\\"llama_version\\\":\\\""
              << v14::json_escape(llama_version() ? llama_version() : "unknown")
              << "\\\",\\\"status\\\":\\\"ROWS_READ\\\","
              << "\\\"source\\\":\\\"RECEIVER_INPUT_TOKEN_EMBEDDING_TABLE\\\","
              << "\\\"model_vocab\\\":" << vocab << ",\\\"embedding_dim\\\":" << dim
              << ",\\\"tensor_type\\\":\\\"" << v14::json_escape(type_name ? type_name : "unknown")
              << "\\\",\\\"row_bytes\\\":" << row_bytes
              << ",\\\"tensor_row_stride_bytes\\\":" << tensor->nb[1]
              << ",\\\"requested_token_ids\\\":[";
    for (std::size_t i = 0; i < token_ids.size(); ++i) {
        if (i) std::cout << ",";
        std::cout << token_ids[i];
    }
    std::cout << "],\\\"rows\\\":[";
    for (std::size_t i = 0; i < rows.size(); ++i) {
        if (i) std::cout << ",";
        std::cout << "{\\\"token_id\\\":" << token_ids[i] << ",\\\"values\\\":[";
        for (std::size_t j = 0; j < rows[i].size(); ++j) {
            if (j) std::cout << ",";
            std::cout << v14::number(rows[i][j]);
        }
        std::cout << "]}";
    }
    std::cout << "],\\\"full_table_copied\\\":false,\\\"read_only\\\":true,\\\"max_rows\\\":"
              << v14::kMaxTokenRows << "}\\n";
    return 0;
}

bool decode_embeddings(llama_context * ctx, int rows, int input_dim, int output_dim,
                       const std::vector<int> & positions, const std::vector<float> & input,
                       std::vector<float> & output, int & decode_status) {
    if (!v14::valid_batch(rows, input_dim, input) || !v14::valid_positions(rows, positions, v14::kMaxPosition)) return false;
    llama_memory_clear(llama_get_memory(ctx), true);
    BatchGuard batch;
    batch.value = llama_batch_init(rows, input_dim, 1);
    batch.active = true;
    if (!batch.value.embd || !batch.value.pos || !batch.value.n_seq_id ||
        !batch.value.seq_id || !batch.value.logits) return false;
    batch.value.n_tokens = rows;
    for (int row = 0; row < rows; ++row) {
        const std::size_t offset = static_cast<std::size_t>(row) * input_dim;
        std::copy_n(input.data() + offset, input_dim, batch.value.embd + offset);
        batch.value.pos[row] = positions[static_cast<std::size_t>(row)];
        batch.value.n_seq_id[row] = 1;
        if (!batch.value.seq_id[row]) return false;
        batch.value.seq_id[row][0] = 0;
        batch.value.logits[row] = 1;
    }
    decode_status = llama_decode(ctx, batch.value);
    if (decode_status != 0) return false;
    output.clear();
    output.reserve(static_cast<std::size_t>(rows) * output_dim);
    for (int row = 0; row < rows; ++row) {
        const float * values = llama_get_embeddings_ith(ctx, row);
        if (!values) return false;
        output.insert(output.end(), values, values + output_dim);
    }
    return v14::all_finite(output);
}

void print_version() {
    const char * version = llama_version();
    std::cout << "{\"schema\":\"v14.native-latent-receiver/2\",\"runner_revision\":\""
              << V14_LLAMA_REVISION << "\",\"llama_version\":\""
              << v14::json_escape(version ? version : "unknown") << "\"}\n";
}

int run_native(const std::string & model_path, int rows, int input_dim, int threads,
               const std::vector<int> & positions, const std::vector<float> & input) {
    if (!v14::valid_batch(rows, input_dim, input)) {
        std::cerr << "invalid input batch\n";
        return 2;
    }
    BackendGuard backend;
    ModelGuard model;
    ContextGuard context;
    llama_model_params model_params = llama_model_default_params();
    model_params.n_gpu_layers = 0;
    model_params.load_mode = LLAMA_LOAD_MODE_MMAP;
    model.value = llama_model_load_from_file(model_path.c_str(), model_params);
    if (!model.value) {
        std::cerr << "model load failed\n";
        return 3;
    }
    const int model_context = llama_model_n_ctx_train(model.value);
    if (model_context <= 0 || !v14::valid_positions(rows, positions, model_context)) {
        std::cerr << "sender position mapping exceeds receiver model context\n";
        return 4;
    }
    int receiver_input_dim = llama_model_n_embd_inp(model.value);
    if (receiver_input_dim <= 0) receiver_input_dim = llama_model_n_embd(model.value);
    int output_dim = llama_model_n_embd_out(model.value);
    if (output_dim <= 0) output_dim = llama_model_n_embd(model.value);
    if (receiver_input_dim <= 0 || output_dim <= 0) {
        std::cerr << "invalid model embedding dimensions\n";
        return 4;
    }
    if (receiver_input_dim != input_dim) {
        std::cout << "{\"schema\":\"v14.native-latent-receiver/2\",\"runner_revision\":\""
                  << V14_LLAMA_REVISION << "\",\"llama_version\":\""
                  << v14::json_escape(llama_version() ? llama_version() : "unknown")
                  << "\",\"status\":\"DIMENSION_MISMATCH\",\"input_rows\":" << rows
                  << ",\"input_dim\":" << input_dim << ",\"receiver_input_dim\":" << receiver_input_dim
                  << ",\"output_dim\":" << output_dim
                  << ",\"position_ids\":" << v14::positions_json(positions)
                  << ",\"position_mode\":\"" << v14::kPositionMode << "\""
                  << ",\"row_shuffle_control_applicable\":false,\"row_shuffle_control_cosine\":null"
                  << ",\"decode_status\":-100,\"finite_output\":false}\n";
        return 0;
    }
    llama_context_params context_params = llama_context_default_params();
    context_params.n_ctx = static_cast<uint32_t>(std::min(model_context, std::max(64, positions.back() + 1)));
    context_params.n_batch = static_cast<uint32_t>(rows);
    context_params.n_ubatch = static_cast<uint32_t>(rows);
    context_params.n_seq_max = 1;
    context_params.n_threads = std::max(1, std::min(threads, 2));
    context_params.n_threads_batch = context_params.n_threads;
    context_params.embeddings = true;
    context_params.pooling_type = LLAMA_POOLING_TYPE_NONE;
    context_params.attention_type = LLAMA_ATTENTION_TYPE_CAUSAL;
    context.value = llama_init_from_model(model.value, context_params);
    if (!context.value) {
        std::cerr << "context init failed\n";
        return 5;
    }

    const auto zero = v14::zero_control(input.size());
    const auto shuffled = v14::shuffle_control(input, rows, input_dim);
    const auto row_shuffled = v14::reverse_rows(input, rows, input_dim);
    std::vector<float> positive_out, zero_out, shuffled_out, row_shuffled_out, repeat_out;
    int positive_status = -999, zero_status = -999, shuffle_status = -999, row_shuffle_status = -999, repeat_status = -999;
    const bool row_shuffle_applicable = rows >= 2;
    if (!decode_embeddings(context.value, rows, input_dim, output_dim, positions, input, positive_out, positive_status) ||
        !decode_embeddings(context.value, rows, input_dim, output_dim, positions, zero, zero_out, zero_status) ||
        !decode_embeddings(context.value, rows, input_dim, output_dim, positions, shuffled, shuffled_out, shuffle_status) ||
        (row_shuffle_applicable && !decode_embeddings(context.value, rows, input_dim, output_dim, positions, row_shuffled, row_shuffled_out, row_shuffle_status)) ||
        !decode_embeddings(context.value, rows, input_dim, output_dim, positions, input, repeat_out, repeat_status)) {
        std::cerr << "native decode or output embedding failed\n";
        return 6;
    }

    const double output_norm = v14::l2_norm(positive_out);
    const double input_effect = v14::rms_delta(positive_out, zero_out);
    std::cout << "{\"schema\":\"v14.native-latent-receiver/2\",\"runner_revision\":\""
              << V14_LLAMA_REVISION << "\",\"llama_version\":\""
              << v14::json_escape(llama_version() ? llama_version() : "unknown")
              << "\",\"status\":\"DECODED\",\"input_rows\":" << rows
              << ",\"input_dim\":" << input_dim << ",\"receiver_input_dim\":" << receiver_input_dim
              << ",\"output_dim\":" << output_dim
              << ",\"position_ids\":" << v14::positions_json(positions)
              << ",\"position_mode\":\"" << v14::kPositionMode << "\""
              << ",\"decode_status\":" << positive_status
              << ",\"output_norm\":" << v14::number(output_norm)
              << ",\"input_effect_rms\":" << v14::number(input_effect)
              << ",\"zero_control_cosine\":" << v14::number(v14::cosine(positive_out, zero_out))
              << ",\"shuffle_control_cosine\":" << v14::number(v14::cosine(positive_out, shuffled_out))
              << ",\"row_shuffle_control_applicable\":" << (row_shuffle_applicable ? "true" : "false")
              << ",\"row_shuffle_control_cosine\":" << v14::number(row_shuffle_applicable ? v14::cosine(positive_out, row_shuffled_out) : std::numeric_limits<double>::quiet_NaN())
              << ",\"repeat_cosine\":" << v14::number(v14::cosine(positive_out, repeat_out))
              << ",\"finite_output\":" << (v14::all_finite(positive_out) ? "true" : "false") << "}\n";
    return 0;
}
}  // namespace
#endif

int main(int argc, char ** argv) {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    if (argc == 2 && std::string(argv[1]) == "--selftest") return v14::selftest();
#ifdef V14_WITH_LLAMA
    if (argc == 2 && std::string(argv[1]) == "--version") {
        print_version();
        return 0;
    }
    if (argc >= 2 && std::string(argv[1]) == "--token-rows") {
        std::string model_path, token_ids_text;
        for (int i = 2; i < argc; ++i) {
            const std::string arg(argv[i]);
            if (arg == "--model" && i + 1 < argc) model_path = argv[++i];
            else if (arg == "--token-ids" && i + 1 < argc) token_ids_text = argv[++i];
            else {
                std::cerr << "unknown or incomplete token-row argument\\n";
                return 64;
            }
        }
        std::vector<int> token_ids;
        if (model_path.empty() || !v14::parse_token_ids(token_ids_text, token_ids)) {
            std::cerr << "usage: native_latent_receiver --token-rows --model PATH --token-ids CSV\\n";
            return 64;
        }
        return run_token_rows(model_path, token_ids);
    }
    std::string model_path, positions_text;
    int rows = 0, input_dim = 0, threads = 1;
    for (int i = 1; i < argc; ++i) {
        const std::string arg(argv[i]);
        if (arg == "--model" && i + 1 < argc) model_path = argv[++i];
        else if (arg == "--rows" && i + 1 < argc) rows = std::atoi(argv[++i]);
        else if (arg == "--input-dim" && i + 1 < argc) input_dim = std::atoi(argv[++i]);
        else if (arg == "--positions" && i + 1 < argc) positions_text = argv[++i];
        else if (arg == "--threads" && i + 1 < argc) threads = std::atoi(argv[++i]);
        else {
            std::cerr << "unknown or incomplete argument\n";
            return 64;
        }
    }
    std::vector<int> positions;
    if (model_path.empty() || rows < 1 || input_dim < 1 || threads < 1 ||
        !v14::valid_batch(rows, input_dim, std::vector<float>(static_cast<std::size_t>(rows) * input_dim, 0.0f)) ||
        !v14::parse_positions(positions_text, rows, positions)) {
        std::cerr << "usage: native_latent_receiver --model PATH --rows N --input-dim D --positions CSV --threads N\n";
        return 64;
    }
    const std::size_t count = static_cast<std::size_t>(rows) * input_dim;
    std::vector<float> input(count);
    std::cin.read(reinterpret_cast<char *>(input.data()), static_cast<std::streamsize>(count * sizeof(float)));
    if (static_cast<std::size_t>(std::cin.gcount()) != count * sizeof(float) ||
        std::cin.peek() != std::char_traits<char>::eof() || !v14::valid_batch(rows, input_dim, input)) {
        std::cerr << "invalid binary input payload\n";
        return 65;
    }
    return run_native(model_path, rows, input_dim, threads, positions, input);
#else
    if (argc == 2 && std::string(argv[1]) == "--version") {
        std::cout << "{\"schema\":\"v14.native-latent-receiver/2\",\"runner_revision\":\""
                  << V14_LLAMA_REVISION << "\",\"llama_version\":\"LOCAL_CORE_ONLY\"}\n";
        return 0;
    }
    std::cerr << "native llama.cpp support was not compiled in\n";
    return 69;
#endif
}
