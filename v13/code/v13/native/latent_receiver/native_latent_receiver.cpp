#include <algorithm>
#include <cmath>
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
#endif

namespace v14 {
constexpr int kMaxRows = 64;
constexpr int kMaxDim = 8192;
constexpr int kMaxPosition = 131072;
constexpr const char * kPositionMode = "ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL";
constexpr std::size_t kMaxElements = 262144;
constexpr double kEffectEpsilon = 1.0e-7;
constexpr double kLogitEffectEpsilon = 1.0e-6;

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

struct TokenSummary {
    int token_id = -1;
    double margin = 0.0;
};

bool summarize_logits(const std::vector<float> & logits, TokenSummary & result) {
    if (logits.size() < 2 || !all_finite(logits)) return false;
    float top1 = -std::numeric_limits<float>::infinity();
    float top2 = -std::numeric_limits<float>::infinity();
    int top1_id = -1;
    for (std::size_t i = 0; i < logits.size(); ++i) {
        const float value = logits[i];
        if (value > top1) {
            top2 = top1;
            top1 = value;
            top1_id = static_cast<int>(i);
        } else if (value > top2) {
            top2 = value;
        }
    }
    if (top1_id < 0 || !std::isfinite(top1) || !std::isfinite(top2) || top1 < top2) return false;
    result.token_id = top1_id;
    result.margin = static_cast<double>(top1) - static_cast<double>(top2);
    return std::isfinite(result.margin) && result.margin >= 0.0;
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
    TokenSummary token_summary;
    if (!summarize_logits(std::vector<float>{1.0f, 3.0f, 2.0f}, token_summary)) return 18;
    if (token_summary.token_id != 1 || std::abs(token_summary.margin - 1.0) > 1.0e-12) return 19;
    if (summarize_logits(std::vector<float>{1.0f, std::numeric_limits<float>::quiet_NaN()}, token_summary)) return 20;
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

struct TokenProbe {
    std::vector<float> logits;
    v14::TokenSummary summary;
};

bool capture_next_token(llama_context * ctx, int vocab_size, TokenProbe & probe) {
    if (vocab_size < 2) return false;
    float * logits = llama_get_logits_ith(ctx, -1);
    if (!logits) return false;
    probe.logits.assign(logits, logits + vocab_size);
    return v14::summarize_logits(probe.logits, probe.summary);
}

bool decode_embeddings(llama_context * ctx, int rows, int input_dim, int output_dim,
                       int vocab_size, const std::vector<int> & positions,
                       const std::vector<float> & input, std::vector<float> & output,
                       int & decode_status, TokenProbe & token_probe) {
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
    if (decode_status != 0 || !capture_next_token(ctx, vocab_size, token_probe)) return false;
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
    std::cout << "{\"schema\":\"v14.native-latent-receiver/3\",\"runner_revision\":\""
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
    const int vocab_size = llama_n_vocab(llama_model_get_vocab(model.value));
    if (receiver_input_dim <= 0 || output_dim <= 0 || vocab_size < 2) {
        std::cerr << "invalid model embedding dimensions\n";
        return 4;
    }
    if (receiver_input_dim != input_dim) {
        std::cout << "{\"schema\":\"v14.native-latent-receiver/3\",\"runner_revision\":\""
                  << V14_LLAMA_REVISION << "\",\"llama_version\":\""
                  << v14::json_escape(llama_version() ? llama_version() : "unknown")
                  << "\",\"status\":\"DIMENSION_MISMATCH\",\"input_rows\":" << rows
                  << ",\"input_dim\":" << input_dim << ",\"receiver_input_dim\":" << receiver_input_dim
                  << ",\"output_dim\":" << output_dim
                  << ",\"position_ids\":" << v14::positions_json(positions)
                  << ",\"position_mode\":\"" << v14::kPositionMode << "\""
                  << ",\"row_shuffle_control_applicable\":false,\"row_shuffle_control_cosine\":null"
                  << ",\"receiver_vocab_size\":" << vocab_size
                  << ",\"receiver_next_token_id\":null,\"zero_control_next_token_id\":null"
                  << ",\"shuffle_control_next_token_id\":null,\"row_shuffle_control_next_token_id\":null"
                  << ",\"repeat_next_token_id\":null,\"receiver_next_token_margin\":null"
                  << ",\"logit_effect_rms\":null,\"logit_cosine\":null"
                  << ",\"next_token_effect_detected\":false,\"next_token_changed_vs_zero\":false"
                  << ",\"next_token_changed_vs_shuffle\":false,\"next_token_changed_vs_row_shuffle\":false"
                  << ",\"repeat_next_token_stable\":false"
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
    TokenProbe positive_token, zero_token, shuffled_token, row_shuffled_token, repeat_token;
    int positive_status = -999, zero_status = -999, shuffle_status = -999, row_shuffle_status = -999, repeat_status = -999;
    const bool row_shuffle_applicable = rows >= 2;
    if (!decode_embeddings(context.value, rows, input_dim, output_dim, vocab_size, positions, input, positive_out, positive_status, positive_token) ||
        !decode_embeddings(context.value, rows, input_dim, output_dim, vocab_size, positions, zero, zero_out, zero_status, zero_token) ||
        !decode_embeddings(context.value, rows, input_dim, output_dim, vocab_size, positions, shuffled, shuffled_out, shuffle_status, shuffled_token) ||
        (row_shuffle_applicable && !decode_embeddings(context.value, rows, input_dim, output_dim, vocab_size, positions, row_shuffled, row_shuffled_out, row_shuffle_status, row_shuffled_token)) ||
        !decode_embeddings(context.value, rows, input_dim, output_dim, vocab_size, positions, input, repeat_out, repeat_status, repeat_token)) {
        std::cerr << "native decode or output embedding failed\n";
        return 6;
    }

    const double output_norm = v14::l2_norm(positive_out);
    const double input_effect = v14::rms_delta(positive_out, zero_out);
    const double logit_effect = v14::rms_delta(positive_token.logits, zero_token.logits);
    const double logit_similarity = v14::cosine(positive_token.logits, zero_token.logits);
    const bool next_token_effect = logit_effect > v14::kLogitEffectEpsilon;
    std::cout << "{\"schema\":\"v14.native-latent-receiver/3\",\"runner_revision\":\""
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
              << ",\"receiver_vocab_size\":" << vocab_size
              << ",\"receiver_next_token_id\":" << positive_token.summary.token_id
              << ",\"zero_control_next_token_id\":" << zero_token.summary.token_id
              << ",\"shuffle_control_next_token_id\":" << shuffled_token.summary.token_id
              << ",\"row_shuffle_control_next_token_id\":"
              << (row_shuffle_applicable ? std::to_string(row_shuffled_token.summary.token_id) : "null")
              << ",\"repeat_next_token_id\":" << repeat_token.summary.token_id
              << ",\"receiver_next_token_margin\":" << v14::number(positive_token.summary.margin)
              << ",\"logit_effect_rms\":" << v14::number(logit_effect)
              << ",\"logit_cosine\":" << v14::number(logit_similarity)
              << ",\"next_token_effect_detected\":" << (next_token_effect ? "true" : "false")
              << ",\"next_token_changed_vs_zero\":" << (positive_token.summary.token_id != zero_token.summary.token_id ? "true" : "false")
              << ",\"next_token_changed_vs_shuffle\":" << (positive_token.summary.token_id != shuffled_token.summary.token_id ? "true" : "false")
              << ",\"next_token_changed_vs_row_shuffle\":" << (row_shuffle_applicable && positive_token.summary.token_id != row_shuffled_token.summary.token_id ? "true" : "false")
              << ",\"repeat_next_token_stable\":" << (positive_token.summary.token_id == repeat_token.summary.token_id ? "true" : "false")
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
        std::cout << "{\"schema\":\"v14.native-latent-receiver/3\",\"runner_revision\":\""
                  << V14_LLAMA_REVISION << "\",\"llama_version\":\"LOCAL_CORE_ONLY\"}\n";
        return 0;
    }
    std::cerr << "native llama.cpp support was not compiled in\n";
    return 69;
#endif
}
