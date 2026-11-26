#include <algorithm>
#include <cmath>
#include <chrono>
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
#include "position_layout.hpp"
#include "native_receiver_kv_snapshot.hpp"
#endif

namespace v14 {
constexpr int kMaxRows = 64;
constexpr int kMaxDim = 8192;
constexpr int kMaxPosition = 131072;
constexpr const char * kPositionMode = "ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL";
constexpr std::size_t kMaxElements = 262144;
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

bool logprob_from_logits(const float * logits, int vocab_size, int token_id, double & result) {
    if (!logits || vocab_size < 1 || token_id < 0 || token_id >= vocab_size) return false;
    double maximum = -std::numeric_limits<double>::infinity();
    for (int i = 0; i < vocab_size; ++i) {
        const double value = static_cast<double>(logits[i]);
        if (std::isnan(value) || (std::isinf(value) && value > 0.0)) return false;
        if (std::isfinite(value)) maximum = std::max(maximum, value);
    }
    if (!std::isfinite(maximum) || !std::isfinite(static_cast<double>(logits[token_id]))) return false;
    long double sum = 0.0L;
    for (int i = 0; i < vocab_size; ++i) {
        const double value = static_cast<double>(logits[i]);
        if (std::isfinite(value)) sum += std::exp(value - maximum);
    }
    if (!(sum > 0.0L) || !std::isfinite(static_cast<double>(sum))) return false;
    result = static_cast<double>(logits[token_id]) - maximum - std::log(static_cast<double>(sum));
    return std::isfinite(result) && result <= 1.0e-7;
}

bool valid_sha256_hex(const std::string & value) {
    if (value.size() != 64) return false;
    return std::all_of(value.begin(), value.end(), [](unsigned char ch) {
        return (ch >= '0' && ch <= '9') || (ch >= 'a' && ch <= 'f');
    });
}


uint32_t rotate_right(uint32_t value, unsigned int shift) {
    return (value >> shift) | (value << (32u - shift));
}

std::string sha256_hex(const std::vector<uint8_t> & input) {
    static const uint32_t constants[64] = {
        0x428a2f98u, 0x71374491u, 0xb5c0fbcfu, 0xe9b5dba5u, 0x3956c25bu, 0x59f111f1u, 0x923f82a4u, 0xab1c5ed5u,
        0xd807aa98u, 0x12835b01u, 0x243185beu, 0x550c7dc3u, 0x72be5d74u, 0x80deb1feu, 0x9bdc06a7u, 0xc19bf174u,
        0xe49b69c1u, 0xefbe4786u, 0x0fc19dc6u, 0x240ca1ccu, 0x2de92c6fu, 0x4a7484aau, 0x5cb0a9dcu, 0x76f988dau,
        0x983e5152u, 0xa831c66du, 0xb00327c8u, 0xbf597fc7u, 0xc6e00bf3u, 0xd5a79147u, 0x06ca6351u, 0x14292967u,
        0x27b70a85u, 0x2e1b2138u, 0x4d2c6dfcu, 0x53380d13u, 0x650a7354u, 0x766a0abbu, 0x81c2c92eu, 0x92722c85u,
        0xa2bfe8a1u, 0xa81a664bu, 0xc24b8b70u, 0xc76c51a3u, 0xd192e819u, 0xd6990624u, 0xf40e3585u, 0x106aa070u,
        0x19a4c116u, 0x1e376c08u, 0x2748774cu, 0x34b0bcb5u, 0x391c0cb3u, 0x4ed8aa4au, 0x5b9cca4fu, 0x682e6ff3u,
        0x748f82eeu, 0x78a5636fu, 0x84c87814u, 0x8cc70208u, 0x90befffau, 0xa4506cebu, 0xbef9a3f7u, 0xc67178f2u
    };
    std::vector<uint8_t> data = input;
    const uint64_t bit_length = static_cast<uint64_t>(data.size()) * 8u;
    data.push_back(0x80u);
    while (data.size() % 64u != 56u) data.push_back(0u);
    for (int shift = 56; shift >= 0; shift -= 8) {
        data.push_back(static_cast<uint8_t>((bit_length >> shift) & 0xffu));
    }

    uint32_t state[8] = {
        0x6a09e667u, 0xbb67ae85u, 0x3c6ef372u, 0xa54ff53au,
        0x510e527fu, 0x9b05688cu, 0x1f83d9abu, 0x5be0cd19u
    };
    for (std::size_t offset = 0; offset < data.size(); offset += 64u) {
        uint32_t words[64] = {};
        for (int i = 0; i < 16; ++i) {
            const std::size_t base = offset + static_cast<std::size_t>(i) * 4u;
            words[i] = (static_cast<uint32_t>(data[base]) << 24u) |
                       (static_cast<uint32_t>(data[base + 1]) << 16u) |
                       (static_cast<uint32_t>(data[base + 2]) << 8u) |
                       static_cast<uint32_t>(data[base + 3]);
        }
        for (int i = 16; i < 64; ++i) {
            const uint32_t x = words[i - 15], y = words[i - 2];
            const uint32_t s0 = rotate_right(x, 7u) ^ rotate_right(x, 18u) ^ (x >> 3u);
            const uint32_t s1 = rotate_right(y, 17u) ^ rotate_right(y, 19u) ^ (y >> 10u);
            words[i] = words[i - 16] + s0 + words[i - 7] + s1;
        }
        uint32_t a = state[0], b = state[1], c = state[2], d = state[3];
        uint32_t e = state[4], f = state[5], g = state[6], h = state[7];
        for (int i = 0; i < 64; ++i) {
            const uint32_t sum1 = rotate_right(e, 6u) ^ rotate_right(e, 11u) ^ rotate_right(e, 25u);
            const uint32_t choose = (e & f) ^ (~e & g);
            const uint32_t temp1 = h + sum1 + choose + constants[i] + words[i];
            const uint32_t sum0 = rotate_right(a, 2u) ^ rotate_right(a, 13u) ^ rotate_right(a, 22u);
            const uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
            const uint32_t temp2 = sum0 + majority;
            h = g; g = f; f = e; e = d + temp1;
            d = c; c = b; b = a; a = temp1 + temp2;
        }
        state[0] += a; state[1] += b; state[2] += c; state[3] += d;
        state[4] += e; state[5] += f; state[6] += g; state[7] += h;
    }

    std::ostringstream output;
    output << std::hex << std::setfill('0');
    for (uint32_t word : state) output << std::setw(8) << word;
    return output.str();
}

std::string target_token_ids_sha256(const std::vector<int32_t> & tokens) {
    std::vector<uint8_t> bytes;
    bytes.reserve(tokens.size() * 4u);
    for (int32_t token : tokens) {
        const uint32_t value = static_cast<uint32_t>(token);
        bytes.push_back(static_cast<uint8_t>(value & 0xffu));
        bytes.push_back(static_cast<uint8_t>((value >> 8u) & 0xffu));
        bytes.push_back(static_cast<uint8_t>((value >> 16u) & 0xffu));
        bytes.push_back(static_cast<uint8_t>((value >> 24u) & 0xffu));
    }
    return sha256_hex(bytes);
}

bool target_token_ids_hash_matches(const std::vector<int32_t> & tokens, const std::string & supplied) {
    if (tokens.empty() || !valid_sha256_hex(supplied) ||
        std::any_of(tokens.begin(), tokens.end(), [](int32_t token) { return token < 0; })) return false;
    return target_token_ids_sha256(tokens) == supplied;
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

#ifdef V14_WITH_LLAMA
int selftest_embedding_positions() {
    const std::vector<int> positions{0, 1, 2};
    const enum llama_rope_type rope_types[] = {
        LLAMA_ROPE_TYPE_NORM, LLAMA_ROPE_TYPE_MROPE, LLAMA_ROPE_TYPE_IMROPE
    };
    for (enum llama_rope_type rope_type : rope_types) {
        llama_batch batch = llama_batch_init(3, 2, 1);
        if (batch.pos == nullptr) {
            llama_batch_free(batch);
            return 21;
        }
        if (!prepare_embedding_positions(batch, rope_type, 3, positions)) {
            llama_batch_free(batch);
            return 22;
        }
        const std::size_t sections = positions_per_embedding(rope_type);
        const std::size_t expected = rope_type == LLAMA_ROPE_TYPE_NORM ? 1u : 4u;
        if (sections != expected) {
            llama_batch_free(batch);
            return 23;
        }
        for (std::size_t section = 0; section < sections; ++section) {
            for (int row = 0; row < 3; ++row) {
                if (batch.pos[section * 3u + static_cast<std::size_t>(row)] != positions[static_cast<std::size_t>(row)]) {
                    llama_batch_free(batch);
                    return 24;
                }
            }
        }
        llama_batch_free(batch);
    }

    llama_batch invalid = llama_batch_init(3, 2, 1);
    if (invalid.pos == nullptr) {
        llama_batch_free(invalid);
        return 25;
    }
    if (prepare_embedding_positions(invalid, LLAMA_ROPE_TYPE_MROPE, 3, std::vector<int>{0, 1})) {
        llama_batch_free(invalid);
        return 26;
    }
    llama_batch_free(invalid);
    return 0;
}
#endif

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
    const float equal_logits[] = {0.0f, 0.0f};
    double logprob = 0.0;
    if (!logprob_from_logits(equal_logits, 2, 0, logprob) || std::abs(logprob + std::log(2.0)) > 1.0e-6) return 18;
    if (logprob_from_logits(equal_logits, 2, 2, logprob)) return 19;
    const float nan_logits[] = {std::numeric_limits<float>::quiet_NaN(), 0.0f};
    if (logprob_from_logits(nan_logits, 2, 0, logprob)) return 20;
#ifdef V14_WITH_LLAMA
    const int position_layout_status = selftest_embedding_positions();
    if (position_layout_status != 0) return position_layout_status;
    const int kv_snapshot_status = native_kv_snapshot_selftest();
    if (kv_snapshot_status != 0) return 50 + kv_snapshot_status;
#endif
    const float positive_infinity_logits[] = {std::numeric_limits<float>::infinity(), 0.0f};
    if (logprob_from_logits(positive_infinity_logits, 2, 0, logprob)) return 21;
    const float negative_infinity_logits[] = {-std::numeric_limits<float>::infinity(), -std::numeric_limits<float>::infinity()};
    if (logprob_from_logits(negative_infinity_logits, 2, 0, logprob)) return 22;
    if (!valid_sha256_hex(std::string(64, 'a')) || valid_sha256_hex(std::string(63, 'a'))) return 23;
    if (sha256_hex(std::vector<uint8_t>{'a', 'b', 'c'}) != "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") return 24;
    const std::vector<int32_t> target_ids{0, 1, 2};
    const std::string target_ids_sha = "ad5dc1478de06a4c2728ea528bd9361a4b945e92a414bf4d180cedaaeaa5f4cc";
    if (!target_token_ids_hash_matches(target_ids, target_ids_sha)) return 25;
    if (target_token_ids_hash_matches(target_ids, std::string(64, 'a'))) return 26;
    if (target_token_ids_hash_matches(std::vector<int32_t>{0, 1, -1}, target_ids_sha)) return 27;
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

bool decode_embeddings(llama_context * ctx, const llama_model * model, int rows, int input_dim, int output_dim,
                       const std::vector<int> & positions, const std::vector<float> & input,
                       std::vector<float> & output, int & decode_status) {
    if (!ctx || !model || !v14::valid_batch(rows, input_dim, input) || !v14::valid_positions(rows, positions, v14::kMaxPosition)) return false;
    llama_memory_clear(llama_get_memory(ctx), true);
    BatchGuard batch;
    batch.value = llama_batch_init(rows, input_dim, 1);
    batch.active = true;
    if (!batch.value.embd || !batch.value.pos || !batch.value.n_seq_id ||
        !batch.value.seq_id || !batch.value.logits) return false;
    batch.value.n_tokens = rows;
    if (!v14::prepare_embedding_positions(batch.value, llama_model_rope_type(model), rows, positions)) return false;
    for (int row = 0; row < rows; ++row) {
        const std::size_t offset = static_cast<std::size_t>(row) * input_dim;
        std::copy_n(input.data() + offset, input_dim, batch.value.embd + offset);
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

bool score_target_tokens(llama_context * ctx, const llama_model * model, int input_rows,
                         const std::vector<int32_t> & target_tokens,
                         std::vector<double> & token_logprobs, int & decode_status) {
    if (!ctx || !model || target_tokens.empty() || target_tokens.size() > 512) return false;
    const llama_vocab * vocab = llama_model_get_vocab(model);
    const int vocab_size = vocab ? llama_vocab_n_tokens(vocab) : 0;
    if (vocab_size < 1) return false;
    token_logprobs.clear();
    token_logprobs.reserve(target_tokens.size());
    decode_status = 0;
    for (std::size_t i = 0; i < target_tokens.size(); ++i) {
        const int32_t token = target_tokens[i];
        if (token < 0 || token >= vocab_size) return false;
        const float * logits = llama_get_logits_ith(ctx, -1);
        double score = 0.0;
        if (!v14::logprob_from_logits(logits, vocab_size, token, score)) return false;
        token_logprobs.push_back(score);
        if (i + 1 < target_tokens.size()) {
            BatchGuard batch;
            batch.value = llama_batch_init(1, 0, 1);
            batch.active = true;
            if (!batch.value.token || !batch.value.pos || !batch.value.n_seq_id ||
                !batch.value.seq_id || !batch.value.logits || !batch.value.seq_id[0]) return false;
            batch.value.n_tokens = 1;
            batch.value.token[0] = static_cast<llama_token>(token);
            batch.value.pos[0] = input_rows + static_cast<int32_t>(i);
            batch.value.n_seq_id[0] = 1;
            batch.value.seq_id[0][0] = 0;
            batch.value.logits[0] = 1;
            decode_status = llama_decode(ctx, batch.value);
            if (decode_status != 0) return false;
        }
    }
    return token_logprobs.size() == target_tokens.size() && decode_status == 0;
}


bool decode_roundtrip_token(llama_context * ctx, int32_t token, int32_t position, int & decode_status) {
    if (!ctx || token < 0 || position < 0) return false;
    BatchGuard batch;
    batch.value = llama_batch_init(1, 0, 1);
    batch.active = true;
    if (!batch.value.token || !batch.value.pos || !batch.value.n_seq_id ||
        !batch.value.seq_id || !batch.value.logits || !batch.value.seq_id[0]) return false;
    batch.value.n_tokens = 1;
    batch.value.token[0] = static_cast<llama_token>(token);
    batch.value.pos[0] = position;
    batch.value.n_seq_id[0] = 1;
    batch.value.seq_id[0][0] = 0;
    batch.value.logits[0] = 1;
    decode_status = llama_decode(ctx, batch.value);
    return decode_status == 0;
}

std::string context_params_sha256(const llama_context_params & params) {
    std::ostringstream material;
    material << "n_ctx=" << params.n_ctx
             << ";n_batch=" << params.n_batch
             << ";n_ubatch=" << params.n_ubatch
             << ";n_seq_max=" << params.n_seq_max
             << ";n_threads=" << params.n_threads
             << ";n_threads_batch=" << params.n_threads_batch
             << ";embeddings=" << (params.embeddings ? 1 : 0)
             << ";pooling_type=" << static_cast<int>(params.pooling_type)
             << ";attention_type=" << static_cast<int>(params.attention_type);
    const std::string text = material.str();
    const std::vector<uint8_t> bytes(text.begin(), text.end());
    return v14::sha256_hex(bytes);
}

std::string logits_step_sha256(const float * logits, int vocab_size) {
    if (!logits || vocab_size < 1) return {};
    static_assert(sizeof(float) == sizeof(uint32_t), "native logits must be IEEE-754 float32");
    std::vector<uint8_t> bytes;
    bytes.reserve(static_cast<std::size_t>(vocab_size) * sizeof(float));
    for (int i = 0; i < vocab_size; ++i) {
        uint32_t bits = 0;
        std::memcpy(&bits, logits + i, sizeof(bits));
        bytes.push_back(static_cast<uint8_t>(bits & 0xffu));
        bytes.push_back(static_cast<uint8_t>((bits >> 8u) & 0xffu));
        bytes.push_back(static_cast<uint8_t>((bits >> 16u) & 0xffu));
        bytes.push_back(static_cast<uint8_t>((bits >> 24u) & 0xffu));
    }
    return v14::sha256_hex(bytes);
}

bool run_hybrid_state_roundtrip(
        llama_context * source,
        llama_model * model,
        const llama_context_params & context_params,
        const std::vector<int32_t> & continuation_tokens,
        int source_context_rows,
        std::string & receipt_json) {
    if (!source || !model || continuation_tokens.empty() ||
        continuation_tokens.size() > 64 || source_context_rows < 1) return false;

    char architecture[128] = {};
    if (llama_model_meta_val_str(model, "general.architecture", architecture, sizeof(architecture)) <= 0 ||
        std::string(architecture).rfind("lfm2", 0) != 0) {
        std::cerr << "full hybrid state roundtrip is restricted to LFM2 architectures\n";
        return false;
    }

    struct ZeroizingState {
        std::vector<uint8_t> bytes;
        ~ZeroizingState() { std::fill(bytes.begin(), bytes.end(), 0u); }
    } state;
    const auto capture_started = std::chrono::steady_clock::now();
    const std::size_t state_size = llama_state_seq_get_size(source, 0);
    if (state_size == 0 || state_size > 512u * 1024u * 1024u) return false;
    state.bytes.resize(state_size);
    const std::size_t copied_bytes = llama_state_seq_get_data(
        source, state.bytes.data(), state.bytes.size(), 0);
    const uint64_t capture_duration_us = static_cast<uint64_t>(
        std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::steady_clock::now() - capture_started).count());
    if (copied_bytes != state_size) return false;
    const std::string state_sha256 = v14::sha256_hex(state.bytes);

    ContextGuard destination;
    destination.value = llama_init_from_model(model, context_params);
    if (!destination.value) return false;

    const std::size_t truncated_bytes = llama_state_seq_set_data(
        destination.value, state.bytes.data(), state_size > 0 ? state_size - 1 : 0, 0);
    const bool truncated_restore_rejected = truncated_bytes != state_size;
    llama_memory_clear(llama_get_memory(destination.value), true);

    const auto restore_started = std::chrono::steady_clock::now();
    const std::size_t restored_bytes = llama_state_seq_set_data(
        destination.value, state.bytes.data(), state.bytes.size(), 0);
    const uint64_t restore_duration_us = static_cast<uint64_t>(
        std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::steady_clock::now() - restore_started).count());
    if (restored_bytes != state_size) return false;

    const llama_vocab * vocab = llama_model_get_vocab(model);
    const int vocab_size = vocab ? llama_vocab_n_tokens(vocab) : 0;
    if (vocab_size < 1) return false;

    std::vector<uint8_t> baseline_digest_material;
    std::vector<uint8_t> restored_digest_material;
    baseline_digest_material.reserve(continuation_tokens.size() * 64u);
    restored_digest_material.reserve(continuation_tokens.size() * 64u);
    uint64_t top1_match_count = 0;
    long double squared_error_sum = 0.0L;
    uint64_t compared_logit_count = 0;
    double max_abs_logit_diff = 0.0;
    int source_decode_status = 0;
    int destination_decode_status = 0;

    for (std::size_t i = 0; i < continuation_tokens.size(); ++i) {
        const int32_t token = continuation_tokens[i];
        if (token < 0 || token >= vocab_size) return false;
        const int32_t position = source_context_rows + static_cast<int32_t>(i);
        if (!decode_roundtrip_token(source, token, position, source_decode_status) ||
            !decode_roundtrip_token(destination.value, token, position, destination_decode_status)) return false;

        const float * source_logits = llama_get_logits_ith(source, -1);
        const float * destination_logits = llama_get_logits_ith(destination.value, -1);
        if (!source_logits || !destination_logits) return false;
        int source_top1 = -1;
        int destination_top1 = -1;
        float source_best = -std::numeric_limits<float>::infinity();
        float destination_best = -std::numeric_limits<float>::infinity();
        for (int j = 0; j < vocab_size; ++j) {
            const float a = source_logits[j];
            const float b = destination_logits[j];
            if (std::isnan(a) || std::isnan(b)) return false;
            if (a > source_best) { source_best = a; source_top1 = j; }
            if (b > destination_best) { destination_best = b; destination_top1 = j; }
            double diff = 0.0;
            if (a == b) {
                diff = 0.0;
            } else if (std::isinf(a) || std::isinf(b)) {
                diff = 1.0e30;
            } else {
                diff = std::abs(static_cast<double>(a) - static_cast<double>(b));
            }
            max_abs_logit_diff = std::max(max_abs_logit_diff, diff);
            squared_error_sum += static_cast<long double>(diff) * diff;
            ++compared_logit_count;
        }
        if (source_top1 >= 0 && source_top1 == destination_top1) ++top1_match_count;

        const std::string source_step_sha = logits_step_sha256(source_logits, vocab_size);
        const std::string destination_step_sha = logits_step_sha256(destination_logits, vocab_size);
        if (!v14::valid_sha256_hex(source_step_sha) ||
            !v14::valid_sha256_hex(destination_step_sha)) return false;
        baseline_digest_material.insert(
            baseline_digest_material.end(), source_step_sha.begin(), source_step_sha.end());
        restored_digest_material.insert(
            restored_digest_material.end(), destination_step_sha.begin(), destination_step_sha.end());
    }

    const double rms_logit_diff = compared_logit_count == 0 ? 0.0 :
        std::sqrt(static_cast<double>(squared_error_sum / compared_logit_count));
    const std::string baseline_logits_sha256 = v14::sha256_hex(baseline_digest_material);
    const std::string restored_logits_sha256 = v14::sha256_hex(restored_digest_material);
    std::fill(state.bytes.begin(), state.bytes.end(), 0u);
    const bool state_buffer_zeroized = std::all_of(
        state.bytes.begin(), state.bytes.end(), [](uint8_t value) { return value == 0u; });
    const std::string params_sha256 = context_params_sha256(context_params);
    const bool roundtrip_passed = truncated_restore_rejected && state_buffer_zeroized &&
        state_size == copied_bytes && state_size == restored_bytes &&
        top1_match_count == continuation_tokens.size() &&
        max_abs_logit_diff <= 1.0e-4 && rms_logit_diff <= 1.0e-5;

    std::ostringstream out;
    out << "{\"schema\":\"v14.native-hybrid-state-roundtrip/1\""
        << ",\"status\":\"READ_ONLY_ROUNDTRIP\""
        << ",\"state_api\":\"LLAMA_STATE_SEQ_GET_SIZE_GET_DATA_SET_DATA\""
        << ",\"state_scope\":\"FULL_HYBRID_SEQUENCE\""
        << ",\"state_components\":[\"ATTENTION_KV\",\"RECURRENT_SHORTCONV\"]"
        << ",\"source_sequence_id\":0,\"destination_sequence_id\":0"
        << ",\"state_bytes\":" << state_size
        << ",\"get_size_bytes\":" << state_size
        << ",\"get_data_bytes\":" << copied_bytes
        << ",\"set_data_bytes\":" << restored_bytes
        << ",\"state_sha256\":\"" << state_sha256 << "\""
        << ",\"capture_duration_us\":" << capture_duration_us
        << ",\"restore_duration_us\":" << restore_duration_us
        << ",\"baseline_logits_sha256\":\"" << baseline_logits_sha256 << "\""
        << ",\"restored_logits_sha256\":\"" << restored_logits_sha256 << "\""
        << ",\"continuation_token_count\":" << continuation_tokens.size()
        << ",\"top1_match_count\":" << top1_match_count
        << ",\"max_abs_logit_diff\":" << v14::number(max_abs_logit_diff)
        << ",\"rms_logit_diff\":" << v14::number(rms_logit_diff)
        << ",\"roundtrip_passed\":" << (roundtrip_passed ? "true" : "false")
        << ",\"truncated_restore_rejected\":" << (truncated_restore_rejected ? "true" : "false")
        << ",\"attention_kv_included\":true,\"recurrent_shortconv_included\":true"
        << ",\"raw_state_exported\":false,\"state_persisted\":false"
        << ",\"state_buffer_zeroized\":" << (state_buffer_zeroized ? "true" : "false")
        << ",\"installed_runtime_touched\":false,\"production_route\":false"
        << ",\"training_authority\":0,\"native_receiver_authority\":0"
        << ",\"context_params_sha256\":\"" << params_sha256 << "\"}";
    receipt_json = out.str();
    return true;
}

void print_version() {
    const char * version = llama_version();
    std::cout << "{\"schema\":\"v14.native-latent-receiver/2\",\"runner_revision\":\""
              << V14_LLAMA_REVISION << "\",\"llama_version\":\""
              << v14::json_escape(version ? version : "unknown")
              << "\",\"target_score_supported\":true,\"target_score_schema\":\"v14.native-receiver-target-score/1\",\"task_matrix_supported\":true,\"task_matrix_schema\":\"v14.native-receiver-task-matrix/1\",\"kv_snapshot_supported\":true,\"kv_snapshot_schema\":\"v14.native-receiver-kv-snapshot/1\",\"hybrid_state_roundtrip_supported\":true,\"hybrid_state_roundtrip_schema\":\"v14.native-hybrid-state-roundtrip/1\"}\n";
}

int run_native(const std::string & model_path, int rows, int input_dim, int threads,
               const std::vector<int> & positions, const std::vector<float> & input,
               const std::vector<int32_t> & target_tokens, const std::string & target_hash) {
    if (!v14::valid_batch(rows, input_dim, input)) {
        std::cerr << "invalid input batch\n";
        return 2;
    }
    const std::string verified_target_hash = target_tokens.empty() ? std::string() : v14::target_token_ids_sha256(target_tokens);
    if (!target_tokens.empty() && !v14::target_token_ids_hash_matches(target_tokens, target_hash)) {
        std::cerr << "target token ID hash mismatch\n";
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
    if (model_context <= 0 || !v14::valid_positions(rows, positions, model_context) ||
        rows + static_cast<int>(target_tokens.size()) > model_context ||
        (!target_tokens.empty() && !v14::valid_sha256_hex(target_hash))) {
        std::cerr << "sender position mapping or target score exceeds receiver model context\n";
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
    context_params.n_ctx = static_cast<uint32_t>(std::min(model_context, std::max(64, positions.back() + 1 + static_cast<int>(target_tokens.size()))));
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
    if (!decode_embeddings(context.value, model.value, rows, input_dim, output_dim, positions, input, positive_out, positive_status)) {
        std::cerr << "native positive decode failed\n";
        return 6;
    }
    std::vector<double> target_logprobs;
    int target_decode_status = positive_status;
    if (!target_tokens.empty() &&
        !score_target_tokens(context.value, model.value, rows, target_tokens, target_logprobs, target_decode_status)) {
        std::cerr << "native teacher-forced target scoring failed\n";
        return 7;
    }
    if (!decode_embeddings(context.value, model.value, rows, input_dim, output_dim, positions, zero, zero_out, zero_status) ||
        !decode_embeddings(context.value, model.value, rows, input_dim, output_dim, positions, shuffled, shuffled_out, shuffle_status) ||
        (row_shuffle_applicable && !decode_embeddings(context.value, model.value, rows, input_dim, output_dim, positions, row_shuffled, row_shuffled_out, row_shuffle_status)) ||
        !decode_embeddings(context.value, model.value, rows, input_dim, output_dim, positions, input, repeat_out, repeat_status)) {
        std::cerr << "native control decode or output embedding failed\n";
        return 6;
    }

    const double output_norm = v14::l2_norm(positive_out);
    const double input_effect = v14::rms_delta(positive_out, zero_out);
    std::ostringstream target_score_json;
    if (!target_tokens.empty()) {
        target_score_json << ",\"target_score\":{\"schema\":\"v14.native-receiver-target-score/1\""
                          << ",\"score_method\":\"TEACHER_FORCED_TARGET_LOGPROB_V1\""
                          << ",\"target_token_count\":" << target_tokens.size()
                          << ",\"target_token_ids_sha256\":\"" << verified_target_hash << "\""
                          << ",\"token_logprobs\":[";
        for (std::size_t i = 0; i < target_logprobs.size(); ++i) {
            if (i) target_score_json << ",";
            target_score_json << v14::number(target_logprobs[i]);
        }
        target_score_json << "],\"decode_status\":" << target_decode_status
                          << ",\"native_input_consumed\":true}";
    }
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
              << target_score_json.str()
              << ",\"finite_output\":" << (v14::all_finite(positive_out) ? "true" : "false") << "}\n";
    return 0;
}

struct MatrixInput {
    std::string condition;
    int rows = 0;
    std::vector<int> positions;
    std::vector<float> values;
};

bool decode_bos(llama_context * ctx, const llama_model * model, int & decode_status) {
    if (!ctx || !model) return false;
    llama_memory_clear(llama_get_memory(ctx), true);
    const llama_vocab * vocab = llama_model_get_vocab(model);
    const llama_token bos = vocab ? llama_vocab_bos(vocab) : -1;
    if (bos < 0) return false;
    BatchGuard batch;
    batch.value = llama_batch_init(1, 0, 1);
    batch.active = true;
    if (!batch.value.token || !batch.value.pos || !batch.value.n_seq_id ||
        !batch.value.seq_id || !batch.value.logits || !batch.value.seq_id[0]) return false;
    batch.value.n_tokens = 1;
    batch.value.token[0] = bos;
    batch.value.pos[0] = 0;
    batch.value.n_seq_id[0] = 1;
    batch.value.seq_id[0][0] = 0;
    batch.value.logits[0] = 1;
    decode_status = llama_decode(ctx, batch.value);
    return decode_status == 0;
}

int run_native_matrix(const std::string & model_path, int input_dim, int threads,
                      const std::vector<MatrixInput> & matrices,
                      const std::vector<int32_t> & target_tokens,
                      const std::string & target_hash,
                      bool include_hybrid_state_roundtrip) {
    const std::vector<std::string> expected_conditions = {
        "NO_MESSAGE", "EXACT_MESSAGE", "LATENT_CANDIDATE", "ZERO",
        "SHUFFLE", "REPEAT", "OOD", "ENTITY_SUBSTITUTION"
    };
    const std::string verified_target_hash = v14::target_token_ids_sha256(target_tokens);
    if (matrices.size() != expected_conditions.size() || target_tokens.empty() ||
        target_tokens.size() > 512 ||
        (include_hybrid_state_roundtrip && target_tokens.size() > 64) ||
        !v14::target_token_ids_hash_matches(target_tokens, target_hash)) return 2;
    int max_rows = 1;
    int max_position = 0;
    for (std::size_t i = 0; i < matrices.size(); ++i) {
        const auto & item = matrices[i];
        if (item.condition != expected_conditions[i] || item.rows < 0 || item.rows > v14::kMaxRows) return 2;
        if (item.rows == 0) {
            if (item.condition != "NO_MESSAGE" || !item.positions.empty() || !item.values.empty()) return 2;
            continue;
        }
        if (item.condition == "NO_MESSAGE" ||
            !v14::valid_batch(item.rows, input_dim, item.values) ||
            !v14::valid_positions(item.rows, item.positions, v14::kMaxPosition) ||
            item.positions.size() != static_cast<std::size_t>(item.rows)) return 2;
        for (int row = 0; row < item.rows; ++row)
            if (item.positions[static_cast<std::size_t>(row)] != row) return 2;
        max_rows = std::max(max_rows, item.rows);
        max_position = std::max(max_position, item.positions.back());
    }
    BackendGuard backend;
    ModelGuard model;
    ContextGuard context;
    llama_model_params model_params = llama_model_default_params();
    model_params.n_gpu_layers = 0;
    model_params.load_mode = LLAMA_LOAD_MODE_MMAP;
    model.value = llama_model_load_from_file(model_path.c_str(), model_params);
    if (!model.value) return 3;
    const int model_context = llama_model_n_ctx_train(model.value);
    if (model_context <= 0 || max_position + 1 + static_cast<int>(target_tokens.size()) > model_context) return 4;
    int receiver_input_dim = llama_model_n_embd_inp(model.value);
    if (receiver_input_dim <= 0) receiver_input_dim = llama_model_n_embd(model.value);
    int output_dim = llama_model_n_embd_out(model.value);
    if (output_dim <= 0) output_dim = llama_model_n_embd(model.value);
    if (receiver_input_dim <= 0 || output_dim <= 0 || receiver_input_dim != input_dim) return 4;
    llama_context_params context_params = llama_context_default_params();
    context_params.n_ctx = static_cast<uint32_t>(std::min(
        model_context, std::max(64, max_position + 1 + static_cast<int>(target_tokens.size()))));
    context_params.n_batch = static_cast<uint32_t>(max_rows);
    context_params.n_ubatch = static_cast<uint32_t>(max_rows);
    context_params.n_seq_max = 1;
    context_params.n_threads = std::max(1, std::min(threads, 2));
    context_params.n_threads_batch = context_params.n_threads;
    context_params.embeddings = true;
    context_params.pooling_type = LLAMA_POOLING_TYPE_NONE;
    context_params.attention_type = LLAMA_ATTENTION_TYPE_CAUSAL;
    context.value = llama_init_from_model(model.value, context_params);
    if (!context.value) return 5;
    std::ostringstream condition_json;
    condition_json << "[";
    std::string hybrid_state_roundtrip_json;
    for (std::size_t i = 0; i < matrices.size(); ++i) {
        const auto & item = matrices[i];
        std::vector<float> output;
        int decode_status = -999;
        const int target_context_rows = item.rows == 0 ? 1 : item.rows;
        const bool decoded = item.rows == 0
            ? decode_bos(context.value, model.value, decode_status)
            : decode_embeddings(context.value, model.value, item.rows, input_dim, output_dim,
                                item.positions, item.values, output, decode_status);
        if (!decoded) return 6;
        if (include_hybrid_state_roundtrip && item.condition == "NO_MESSAGE") {
            if (!run_hybrid_state_roundtrip(context.value, model.value, context_params,
                                            target_tokens, target_context_rows,
                                            hybrid_state_roundtrip_json) ||
                !decode_bos(context.value, model.value, decode_status)) {
                std::cerr << "native full-hybrid same-model roundtrip failed\n";
                return 9;
            }
        }
        v14::NativeKvSnapshot kv_snapshot;
        std::string kv_snapshot_error;
        if (!v14::capture_readonly_kv_snapshot(context.value, 0, kv_snapshot, kv_snapshot_error)) {
            std::cerr << "native read-only K/V snapshot failed: " << kv_snapshot_error << "\\n";
            return 8;
        }
        if (kv_snapshot.active_cell_count != static_cast<uint32_t>(target_context_rows) ||
            kv_snapshot.position_ids.size() != static_cast<size_t>(target_context_rows)) return 8;
        for (int32_t row = 0; row < target_context_rows; ++row) {
            if (kv_snapshot.position_ids[static_cast<size_t>(row)] != row) return 8;
        }
        std::vector<double> token_logprobs;
        int target_decode_status = decode_status;
        if (!score_target_tokens(context.value, model.value, target_context_rows,
                                 target_tokens, token_logprobs, target_decode_status)) return 7;
        if (i) condition_json << ",";
        condition_json << "{\"condition\":\"" << item.condition << "\""
                       << ",\"input_rows\":" << item.rows
                       << ",\"context_rows\":" << target_context_rows
                       << ",\"input_dim\":" << input_dim
                       << ",\"position_ids\":" << v14::positions_json(item.positions)
                       << ",\"position_mode\":\"" << v14::kPositionMode << "\""
                       << ",\"decode_status\":" << decode_status
                       << ",\"native_input_consumed\":true"
                       << ",\"kv_snapshot\":" << v14::native_kv_snapshot_json(kv_snapshot)
                       << ",\"target_score\":{\"schema\":\"v14.native-receiver-target-score/1\""
                       << ",\"score_method\":\"TEACHER_FORCED_TARGET_LOGPROB_V1\""
                       << ",\"target_token_count\":" << target_tokens.size()
                       << ",\"target_token_ids_sha256\":\"" << verified_target_hash << "\""
                       << ",\"token_logprobs\":[";
        for (std::size_t j = 0; j < token_logprobs.size(); ++j) {
            if (j) condition_json << ",";
            condition_json << v14::number(token_logprobs[j]);
        }
        condition_json << "],\"decode_status\":" << target_decode_status
                       << ",\"native_input_consumed\":true}}";
    }
    condition_json << "]";
    std::cout << "{\"schema\":\"v14.native-receiver-task-matrix/1\""
              << ",\"runner_revision\":\"" << V14_LLAMA_REVISION << "\""
              << ",\"llama_version\":\"" << v14::json_escape(llama_version() ? llama_version() : "unknown") << "\""
              << ",\"status\":\"SCORED\""
              << ",\"receiver_input_dim\":" << receiver_input_dim
              << ",\"output_dim\":" << output_dim
              << ",\"target_token_count\":" << target_tokens.size()
              << ",\"target_token_ids_sha256\":\"" << verified_target_hash << "\""
              << ",\"conditions\":" << condition_json.str();
    if (include_hybrid_state_roundtrip) {
        if (hybrid_state_roundtrip_json.empty()) return 9;
        std::cout << ",\"hybrid_state_roundtrip\":" << hybrid_state_roundtrip_json;
    }
    std::cout << "}\n";
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
    std::string model_path, positions_text, target_hash, conditions_text;
    int rows = 0, input_dim = 0, threads = 1, target_count = 0, matrix_count = 0;
    bool include_hybrid_state_roundtrip = false;
    for (int i = 1; i < argc; ++i) {
        const std::string arg(argv[i]);
        if (arg == "--model" && i + 1 < argc) model_path = argv[++i];
        else if (arg == "--rows" && i + 1 < argc) rows = std::atoi(argv[++i]);
        else if (arg == "--input-dim" && i + 1 < argc) input_dim = std::atoi(argv[++i]);
        else if (arg == "--positions" && i + 1 < argc) positions_text = argv[++i];
        else if (arg == "--threads" && i + 1 < argc) threads = std::atoi(argv[++i]);
        else if (arg == "--target-count" && i + 1 < argc) target_count = std::atoi(argv[++i]);
        else if (arg == "--target-token-ids-sha256" && i + 1 < argc) target_hash = argv[++i];
        else if (arg == "--matrix-count" && i + 1 < argc) matrix_count = std::atoi(argv[++i]);
        else if (arg == "--conditions" && i + 1 < argc) conditions_text = argv[++i];
        else if (arg == "--hybrid-state-roundtrip") include_hybrid_state_roundtrip = true;
        else {
            std::cerr << "unknown or incomplete argument\n";
            return 64;
        }
    }
    if (matrix_count > 0) {
        const std::vector<std::string> expected_conditions = {
            "NO_MESSAGE", "EXACT_MESSAGE", "LATENT_CANDIDATE", "ZERO",
            "SHUFFLE", "REPEAT", "OOD", "ENTITY_SUBSTITUTION"
        };
        std::vector<std::string> conditions;
        std::stringstream condition_stream(conditions_text);
        std::string condition;
        while (std::getline(condition_stream, condition, ',')) conditions.push_back(condition);
        if (model_path.empty() || rows != 0 || !positions_text.empty() || input_dim < 1 ||
            threads < 1 || matrix_count != static_cast<int>(expected_conditions.size()) ||
            conditions != expected_conditions || target_count < 1 || target_count > 512 ||
            (include_hybrid_state_roundtrip && target_count > 64) ||
            !v14::valid_sha256_hex(target_hash)) {
            std::cerr << "usage: native_latent_receiver --model PATH --matrix-count 8 --conditions CSV --input-dim D --threads N --target-count N --target-token-ids-sha256 SHA256\n";
            return 64;
        }
        std::vector<MatrixInput> matrices;
        matrices.reserve(static_cast<std::size_t>(matrix_count));
        for (int i = 0; i < matrix_count; ++i) {
            int32_t matrix_rows = -1;
            std::cin.read(reinterpret_cast<char *>(&matrix_rows), sizeof(matrix_rows));
            if (std::cin.gcount() != static_cast<std::streamsize>(sizeof(matrix_rows)) ||
                matrix_rows < 0 || matrix_rows > v14::kMaxRows) {
                std::cerr << "invalid matrix row header\n";
                return 65;
            }
            MatrixInput item;
            item.condition = conditions[static_cast<std::size_t>(i)];
            item.rows = matrix_rows;
            if (item.rows > 0) {
                item.positions.resize(static_cast<std::size_t>(item.rows));
                const std::size_t position_bytes = static_cast<std::size_t>(item.rows) * sizeof(int32_t);
                std::cin.read(reinterpret_cast<char *>(item.positions.data()), static_cast<std::streamsize>(position_bytes));
                if (std::cin.gcount() != static_cast<std::streamsize>(position_bytes)) {
                    std::cerr << "truncated matrix position payload\n";
                    return 65;
                }
                item.values.resize(static_cast<std::size_t>(item.rows) * input_dim);
                const std::size_t value_bytes = item.values.size() * sizeof(float);
                std::cin.read(reinterpret_cast<char *>(item.values.data()), static_cast<std::streamsize>(value_bytes));
                if (std::cin.gcount() != static_cast<std::streamsize>(value_bytes) ||
                    !v14::valid_batch(item.rows, input_dim, item.values) ||
                    !v14::valid_positions(item.rows, item.positions, v14::kMaxPosition)) {
                    std::cerr << "invalid matrix embedding payload\n";
                    return 65;
                }
            } else if (item.condition != "NO_MESSAGE") {
                std::cerr << "empty input is allowed only for NO_MESSAGE\n";
                return 65;
            }
            matrices.push_back(std::move(item));
        }
        std::vector<int32_t> target_tokens(static_cast<std::size_t>(target_count));
        const std::size_t target_bytes = static_cast<std::size_t>(target_count) * sizeof(int32_t);
        std::cin.read(reinterpret_cast<char *>(target_tokens.data()), static_cast<std::streamsize>(target_bytes));
        if (std::cin.gcount() != static_cast<std::streamsize>(target_bytes) ||
            std::any_of(target_tokens.begin(), target_tokens.end(), [](int32_t token) { return token < 0; })) {
            std::cerr << "invalid binary target-token payload\n";
            return 66;
        }
        if (std::cin.peek() != std::char_traits<char>::eof()) {
            std::cerr << "unexpected trailing binary input payload\n";
            return 67;
        }
        return run_native_matrix(model_path, input_dim, threads, matrices, target_tokens, target_hash,
                                  include_hybrid_state_roundtrip);
    }
    std::vector<int> positions;
    if (include_hybrid_state_roundtrip || model_path.empty() || rows < 1 || input_dim < 1 || threads < 1 ||
        target_count < 0 || target_count > 512 ||
        (target_count == 0 && !target_hash.empty()) ||
        (target_count > 0 && !v14::valid_sha256_hex(target_hash)) ||
        !v14::valid_batch(rows, input_dim, std::vector<float>(static_cast<std::size_t>(rows) * input_dim, 0.0f)) ||
        !v14::parse_positions(positions_text, rows, positions)) {
        std::cerr << "usage: native_latent_receiver --model PATH --rows N --input-dim D --positions CSV --threads N [--target-count N --target-token-ids-sha256 SHA256] [--hybrid-state-roundtrip]\n";
        return 64;
    }
    const std::size_t count = static_cast<std::size_t>(rows) * input_dim;
    std::vector<float> input(count);
    std::cin.read(reinterpret_cast<char *>(input.data()), static_cast<std::streamsize>(count * sizeof(float)));
    if (std::cin.gcount() != static_cast<std::streamsize>(count * sizeof(float)) ||
        !v14::valid_batch(rows, input_dim, input)) {
        std::cerr << "invalid binary embedding payload\n";
        return 65;
    }
    std::vector<int32_t> target_tokens(static_cast<std::size_t>(target_count));
    if (target_count > 0) {
        const std::size_t target_bytes = static_cast<std::size_t>(target_count) * sizeof(int32_t);
        std::cin.read(reinterpret_cast<char *>(target_tokens.data()), static_cast<std::streamsize>(target_bytes));
        if (std::cin.gcount() != static_cast<std::streamsize>(target_bytes) ||
            std::any_of(target_tokens.begin(), target_tokens.end(), [](int32_t token) { return token < 0; })) {
            std::cerr << "invalid binary target-token payload\n";
            return 66;
        }
    }
    if (std::cin.peek() != std::char_traits<char>::eof()) {
        std::cerr << "unexpected trailing binary input payload\n";
        return 67;
    }
    return run_native(model_path, rows, input_dim, threads, positions, input, target_tokens, target_hash);
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
