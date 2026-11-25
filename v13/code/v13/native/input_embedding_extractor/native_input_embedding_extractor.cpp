#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include <llama.h>
#include "llama-ext.h"
#include <gguf.h>
#include <ggml.h>
#include <sys/stat.h>

#ifndef V14_LLAMA_REVISION
#define V14_LLAMA_REVISION "2851b3bcbf8d993a2243ae751c0a7dfa8e944a40"
#endif

namespace v14 {
constexpr std::size_t kMinTokens = 2;
constexpr std::size_t kMaxTokens = 64;
constexpr std::size_t kMaxDim = 8192;
constexpr std::size_t kMaxElements = kMaxTokens * kMaxDim;
constexpr std::size_t kMaxModelRevision = 160;
constexpr const char * kOutputSchema = "v14.native-input-embedding-extractor/1";
constexpr const char * kReceiptSchema = "v14.llama-token-embedding-rows-receipt/1";
constexpr const char * kApiSymbol = "llama_model_get_tok_embd_rows";
constexpr const char * kApiHeader = "src/llama-ext.h";
constexpr const char * kApiStability = "STAGING_WIP";

struct Options {
    std::string model_path;
    std::string model_revision;
    std::string model_sha256;
    std::string extractor_sha256;
    std::string token_ids;
};

void quiet_log(enum ggml_log_level, const char *, void *) {}

bool is_hex_sha256(const std::string & value) {
    if (value.size() != 64) return false;
    for (char ch : value) {
        if (!((ch >= '0' && ch <= '9') || (ch >= 'a' && ch <= 'f'))) return false;
    }
    return true;
}

bool valid_model_revision(const std::string & value) {
    if (value.empty() || value.size() > kMaxModelRevision) return false;
    for (unsigned char ch : value) {
        if (ch < 0x21 || ch > 0x7e) return false;
    }
    return true;
}

bool parse_token_ids(const std::string & raw, std::vector<llama_token> & ids) {
    ids.clear();
    if (raw.empty() || raw.size() > 4096) return false;
    std::size_t start = 0;
    while (start <= raw.size()) {
        const std::size_t comma = raw.find(',', start);
        const std::size_t end = comma == std::string::npos ? raw.size() : comma;
        if (end == start) return false;
        const std::string item = raw.substr(start, end - start);
        if (!std::all_of(item.begin(), item.end(), [](char ch) { return ch >= '0' && ch <= '9'; })) {
            return false;
        }
        errno = 0;
        char * tail = nullptr;
        const long long value = std::strtoll(item.c_str(), &tail, 10);
        if (errno != 0 || tail == item.c_str() || *tail != '\0'
                || value < 0 || value > std::numeric_limits<llama_token>::max()) {
            return false;
        }
        ids.push_back(static_cast<llama_token>(value));
        if (ids.size() > kMaxTokens) return false;
        if (comma == std::string::npos) break;
        start = comma + 1;
    }
    return ids.size() >= kMinTokens && ids.size() <= kMaxTokens;
}

bool prevalidate_token_ids(
        const std::vector<llama_token> & ids,
        int vocab_size,
        int embedding_dim,
        std::uint32_t & expected_elements) {
    expected_elements = 0;
    if (ids.size() < kMinTokens || ids.size() > kMaxTokens
            || vocab_size < 2 || embedding_dim < 1
            || static_cast<std::size_t>(embedding_dim) > kMaxDim) {
        return false;
    }
    const std::size_t elements = ids.size() * static_cast<std::size_t>(embedding_dim);
    if (elements == 0 || elements > kMaxElements
            || elements > std::numeric_limits<std::uint32_t>::max()) {
        return false;
    }
    for (llama_token token : ids) {
        if (token < 0 || token >= vocab_size) return false;
    }
    expected_elements = static_cast<std::uint32_t>(elements);
    return true;
}

template <typename FetchRows>
bool collect_rows(
        const std::vector<llama_token> & ids,
        int vocab_size,
        int embedding_dim,
        FetchRows fetch_rows,
        std::vector<float> & rows,
        std::uint32_t & elements_written) {
    std::uint32_t expected = 0;
    elements_written = 0;
    rows.clear();
    if (!prevalidate_token_ids(ids, vocab_size, embedding_dim, expected)) return false;

    rows.assign(expected, 0.0f);
    elements_written = fetch_rows(
        ids.data(), static_cast<std::uint32_t>(ids.size()), rows.data());
    if (elements_written != expected) {
        std::fill(rows.begin(), rows.end(), 0.0f);
        return false;
    }
    for (std::size_t row = 0; row < ids.size(); ++row) {
        long double norm_squared = 0.0L;
        const std::size_t offset = row * static_cast<std::size_t>(embedding_dim);
        for (int col = 0; col < embedding_dim; ++col) {
            const float value = rows[offset + static_cast<std::size_t>(col)];
            if (!std::isfinite(value) || std::abs(value) > 1.0e6f) {
                std::fill(rows.begin(), rows.end(), 0.0f);
                return false;
            }
            norm_squared += static_cast<long double>(value) * value;
        }
        if (!std::isfinite(static_cast<double>(norm_squared)) || norm_squared <= 1.0e-20L) {
            std::fill(rows.begin(), rows.end(), 0.0f);
            return false;
        }
    }
    return true;
}

bool parse_options(int argc, char ** argv, Options & options) {
    std::map<std::string, std::string> values;
    const std::vector<std::string> allowed = {
        "--model", "--model-revision", "--model-sha256",
        "--extractor-sha256", "--token-ids"
    };
    for (int i = 2; i < argc; i += 2) {
        if (i + 1 >= argc) return false;
        const std::string key(argv[i]);
        if (std::find(allowed.begin(), allowed.end(), key) == allowed.end()
                || values.find(key) != values.end()) {
            return false;
        }
        values.emplace(key, argv[i + 1]);
    }
    if (values.size() != allowed.size()) return false;
    options.model_path = values["--model"];
    options.model_revision = values["--model-revision"];
    options.model_sha256 = values["--model-sha256"];
    options.extractor_sha256 = values["--extractor-sha256"];
    options.token_ids = values["--token-ids"];
    return !options.model_path.empty() && options.model_path.size() <= 4096
        && valid_model_revision(options.model_revision)
        && is_hex_sha256(options.model_sha256)
        && is_hex_sha256(options.extractor_sha256);
}

std::string json_escape(const std::string & value) {
    std::ostringstream out;
    for (unsigned char ch : value) {
        switch (ch) {
            case '"': out << "\\\""; break;
            case '\\': out << "\\\\"; break;
            case '\b': out << "\\b"; break;
            case '\f': out << "\\f"; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default:
                if (ch < 0x20) {
                    out << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                        << static_cast<unsigned int>(ch) << std::dec;
                } else {
                    out << static_cast<char>(ch);
                }
        }
    }
    return out.str();
}

void print_version() {
    std::cout << "{\"schema\":\"" << kOutputSchema
              << "\",\"llama_cpp_revision\":\"" << V14_LLAMA_REVISION
              << "\",\"api_symbol\":\"" << kApiSymbol
              << "\",\"api_header\":\"" << kApiHeader
              << "\",\"api_stability\":\"" << kApiStability << "\"}\n";
}

int selftest() {
    std::vector<llama_token> ids;
    if (!parse_token_ids("0,17,17", ids) || ids.size() != 3) return 1;
    if (parse_token_ids("1,,2", ids)) return 2;
    if (parse_token_ids("-1,2", ids)) return 3;
    if (parse_token_ids("+1,2", ids)) return 4;
    if (parse_token_ids(" 1,2", ids)) return 5;
    if (parse_token_ids("1,2,", ids)) return 6;
    std::string too_many;
    for (int i = 0; i < 65; ++i) {
        if (i) too_many += ",";
        too_many += "1";
    }
    if (parse_token_ids(too_many, ids)) return 7;

    ids = {0, 3};
    std::vector<float> rows;
    std::uint32_t written = 0;
    int calls = 0;
    bool ok = collect_rows(ids, 4, 2,
        [&](const llama_token * tokens, std::uint32_t count, float * out) {
            ++calls;
            if (count != 2 || tokens[0] != 0 || tokens[1] != 3) return 0U;
            out[0] = 1.0f; out[1] = 2.0f; out[2] = 3.0f; out[3] = 4.0f;
            return 4U;
        }, rows, written);
    if (!ok || calls != 1 || written != 4 || rows.size() != 4 || rows[3] != 4.0f) return 8;

    ids = {0, 4};
    calls = 0;
    ok = collect_rows(ids, 4, 2,
        [&](const llama_token *, std::uint32_t, float *) {
            ++calls;
            return 4U;
        }, rows, written);
    if (ok || calls != 0 || !rows.empty()) return 9;

    ids = {0, 1};
    ok = collect_rows(ids, 4, 2,
        [](const llama_token *, std::uint32_t, float * out) {
            out[0] = 1.0f; out[1] = 2.0f; out[2] = 3.0f; out[3] = 4.0f;
            return 3U;
        }, rows, written);
    if (ok || written != 3 || rows.size() != 4
            || std::any_of(rows.begin(), rows.end(), [](float value) { return value != 0.0f; })) return 10;

    ok = collect_rows(ids, 4, 2,
        [](const llama_token *, std::uint32_t, float * out) {
            out[0] = 1.0f; out[1] = 2.0f;
            out[2] = std::numeric_limits<float>::quiet_NaN(); out[3] = 4.0f;
            return 4U;
        }, rows, written);
    if (ok || std::any_of(rows.begin(), rows.end(), [](float value) { return value != 0.0f; })) return 11;

    std::cout << "{\"schema\":\"" << kOutputSchema
              << "\",\"status\":\"PASS\",\"checks\":11}\n";
    return 0;
}

void print_result(
        const Options & options,
        const std::vector<llama_token> & ids,
        const std::vector<float> & rows,
        int vocab_size,
        int embedding_dim,
        const std::string & source_tensor_type,
        std::uint32_t elements_written) {
    std::cout << "{\"schema\":\"" << kOutputSchema << "\",\"status\":\"COMPLETE\",\"receipt\":{"
              << "\"schema\":\"" << kReceiptSchema << "\","
              << "\"api_symbol\":\"" << kApiSymbol << "\","
              << "\"api_header\":\"" << kApiHeader << "\","
              << "\"api_stability\":\"" << kApiStability << "\","
              << "\"llama_cpp_revision\":\"" << V14_LLAMA_REVISION << "\","
              << "\"extractor_binary_sha256\":\"" << options.extractor_sha256 << "\","
              << "\"model_revision\":\"" << json_escape(options.model_revision) << "\","
              << "\"model_sha256\":\"" << options.model_sha256 << "\","
              << "\"source_tensor_type\":\"" << source_tensor_type << "\","
              << "\"output_dtype\":\"f32\","
              << "\"vocab_size\":" << vocab_size << ","
              << "\"embedding_dim\":" << embedding_dim << ","
              << "\"requested_token_ids\":[";
    for (std::size_t i = 0; i < ids.size(); ++i) {
        if (i) std::cout << ",";
        std::cout << ids[i];
    }
    std::cout << "],\"elements_written\":" << elements_written << "},\"rows\":[";
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    for (std::size_t row = 0; row < ids.size(); ++row) {
        if (row) std::cout << ",";
        std::cout << "[";
        for (int col = 0; col < embedding_dim; ++col) {
            if (col) std::cout << ",";
            std::cout << rows[row * static_cast<std::size_t>(embedding_dim)
                              + static_cast<std::size_t>(col)];
        }
        std::cout << "]";
    }
    std::cout << "]}\n";
}

int extract(const Options & options) {
    struct stat model_stat {};
    if (lstat(options.model_path.c_str(), &model_stat) != 0
            || !S_ISREG(model_stat.st_mode) || model_stat.st_size <= 0) {
        std::cerr << "model file is not a regular non-symlink file\n";
        return 2;
    }

    std::vector<llama_token> ids;
    if (!parse_token_ids(options.token_ids, ids)) {
        std::cerr << "token IDs must contain 2..64 comma-separated nonnegative integers\n";
        return 2;
    }

    llama_backend_init();
    llama_log_set(quiet_log, nullptr);

    llama_model_params params = llama_model_default_params();
    params.n_gpu_layers = 0;
    params.use_mmap = true;
    params.use_mlock = false;
    llama_model * model = llama_model_load_from_file(options.model_path.c_str(), params);
    if (!model) {
        llama_backend_free();
        std::cerr << "native model load failed\n";
        return 3;
    }

    const llama_vocab * vocab = llama_model_get_vocab(model);
    const int vocab_size = vocab ? llama_vocab_n_tokens(vocab) : 0;
    const int embedding_dim = llama_model_n_embd_inp(model);
    std::uint32_t expected_elements = 0;
    if (!prevalidate_token_ids(ids, vocab_size, embedding_dim, expected_elements)) {
        llama_model_free(model);
        llama_backend_free();
        std::cerr << "token IDs or receiver embedding geometry are invalid\n";
        return 4;
    }

    gguf_init_params gguf_params {};
    gguf_params.no_alloc = true;
    gguf_params.ctx = nullptr;
    gguf_context * gguf = gguf_init_from_file(options.model_path.c_str(), gguf_params);
    if (!gguf) {
        llama_model_free(model);
        llama_backend_free();
        std::cerr << "GGUF tensor metadata unavailable\n";
        return 5;
    }
    const std::int64_t tensor_id = gguf_find_tensor(gguf, "token_embd.weight");
    const std::int64_t * tensor_ne = tensor_id >= 0 ? gguf_get_tensor_ne(gguf, tensor_id) : nullptr;
    const char * tensor_type = tensor_id >= 0
        ? ggml_type_name(gguf_get_tensor_type(gguf, tensor_id)) : nullptr;
    if (!tensor_ne || !tensor_type || !*tensor_type
            || tensor_ne[0] != embedding_dim || tensor_ne[1] != vocab_size) {
        gguf_free(gguf);
        llama_model_free(model);
        llama_backend_free();
        std::cerr << "token embedding tensor geometry/type mismatch\n";
        return 6;
    }

    std::vector<float> rows;
    std::uint32_t elements_written = 0;
    const bool ok = collect_rows(ids, vocab_size, embedding_dim,
        [&](const llama_token * tokens, std::uint32_t count, float * out) {
            return llama_model_get_tok_embd_rows(model, tokens, count, out);
        }, rows, elements_written);
    if (!ok || elements_written != expected_elements) {
        gguf_free(gguf);
        llama_model_free(model);
        llama_backend_free();
        std::cerr << "native token embedding extractor returned incomplete or invalid rows\n";
        return 7;
    }

    print_result(options, ids, rows, vocab_size, embedding_dim, tensor_type, elements_written);
    gguf_free(gguf);
    llama_model_free(model);
    llama_backend_free();
    return 0;
}
} // namespace v14

int main(int argc, char ** argv) {
    if (argc == 2 && std::string(argv[1]) == "--version") {
        v14::print_version();
        return 0;
    }
    if (argc == 2 && std::string(argv[1]) == "--selftest") {
        return v14::selftest();
    }
    if (argc < 2 || std::string(argv[1]) != "--extract") {
        std::cerr << "usage: native_input_embedding_extractor --extract --model PATH "
                     "--model-revision REV --model-sha256 SHA256 "
                     "--extractor-sha256 SHA256 --token-ids CSV\n";
        return 2;
    }
    v14::Options options;
    if (!v14::parse_options(argc, argv, options)) {
        std::cerr << "invalid native input embedding extractor arguments\n";
        return 2;
    }
    return v14::extract(options);
}
