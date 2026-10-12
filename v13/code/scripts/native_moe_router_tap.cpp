// WP-N11 native router tap (isolated candidate): read-only cb_eval capture of MoE routing inside llama.cpp, the
// phone runner. For every MoE layer il it copies, per prompt token,
//   ffn_moe_logits-il  router logits            [n_expert]
//   ffn_norm-il        router input (normed)    [n_embd]
//   attn_norm-il       input norm of the block  [n_embd]   (shared pre-router state, if the graph names it)
//   l_out-il           residual after block il  [n_embd]   (= raw input of block il+1; SmallThinker routes on it)
// The model output is not changed (the callback only observes). Same quantities as scripts/moe_router_bench.py
// (HF), so moe_router_monitor.compare() can measure runner/quantisation parity and on-device router stability.
// Usage: native-moe-router-tap <model.gguf> <ids.jsonl> <out_dir> [threads]
//   ids.jsonl: one JSON array of token ids per line (tokenised by the caller, BOS included if wanted).
//   Writes <out_dir>/<line>.<tensor>-<il>.f32 (row-major [n_tokens, width]) and <out_dir>/index.jsonl.
#include "llama.h"
#include "ggml.h"
#include "ggml-backend.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

struct Tap {
    std::map<std::string, std::vector<float>> data;  // name -> [n_tokens * width]
    std::map<std::string, int64_t> width;
};

// Exact names "<prefix>-<layer>" only (graphs also emit e.g. "ffn_norm-3 (reshaped)").
// V13_TAP_NAMES=comma list of prefixes overrides the default set.
static std::vector<std::string> g_prefixes = {"ffn_moe_logits", "ffn_norm", "attn_norm", "l_out"};

static bool wanted(const char * name) {
    for (const auto & p : g_prefixes) {
        const size_t n = p.size();
        if (std::strncmp(name, p.c_str(), n) != 0 || name[n] != '-') continue;
        const char * q = name + n + 1;
        if (!*q) return false;
        for (; *q; ++q) if (*q < '0' || *q > '9') return false;
        return true;
    }
    return false;
}

static bool observe(struct ggml_tensor * t, bool ask, void * user) {
    if (!wanted(t->name)) return ask ? false : true;
    if (ask) return true;
    if (t->type != GGML_TYPE_F32) return true;
    Tap * tap = (Tap *) user;
    const int64_t w = t->ne[0], n = ggml_nelements(t) / w;
    std::vector<float> buf(ggml_nelements(t));
    ggml_backend_tensor_get(t, buf.data(), 0, ggml_nbytes(t));
    // ne[0] is the fastest dimension: rows are tokens when the tensor is contiguous [w, n].
    if (!ggml_is_contiguous(t)) return true;
    // Some names are emitted twice per layer (rms_norm, then the weighted result): keep the last one.
    tap->data[t->name].assign(buf.begin(), buf.begin() + w * n);
    tap->width[t->name] = w;
    return true;
}

static std::vector<llama_token> parse_ids(const std::string & line) {
    std::vector<llama_token> ids; std::string num;
    for (char c : line) {
        if ((c >= '0' && c <= '9') || c == '-') num += c;
        else if (!num.empty()) { ids.push_back((llama_token) std::atol(num.c_str())); num.clear(); }
    }
    if (!num.empty()) ids.push_back((llama_token) std::atol(num.c_str()));
    return ids;
}

int main(int argc, char ** argv) {
    if (argc < 4) { std::fprintf(stderr, "usage: %s model.gguf ids.jsonl out_dir [threads]\n", argv[0]); return 1; }
    const int threads = argc > 4 ? std::atoi(argv[4]) : 4;
    const std::string out = argv[3];
    if (const char * env = std::getenv("V13_TAP_NAMES")) {
        g_prefixes.clear(); std::string cur;
        for (const char * c = env; ; ++c) {
            if (*c == ',' || !*c) { if (!cur.empty()) g_prefixes.push_back(cur); cur.clear(); if (!*c) break; }
            else cur += *c;
        }
    }
    llama_backend_init();
    auto mp = llama_model_default_params(); mp.n_gpu_layers = 0;
    // V13_NO_REPACK=1: keep weights in the mmap'd file layout (no CPU repack copy) to see resident memory without it.
    if (std::getenv("V13_NO_REPACK")) mp.use_extra_bufts = false;
    llama_model * model = llama_model_load_from_file(argv[1], mp); if (!model) return 3;
    Tap tap;
    // V13_TAP_NAMES set but empty = plain inference (no tap, phone-like batch, output only for the last token):
    // used to measure resident memory without the tap's all-token logits and buffers.
    const char * names_env = std::getenv("V13_TAP_NAMES");
    const bool plain = names_env && !*names_env;
    auto cp = llama_context_default_params(); cp.n_ctx = plain ? 2048 : 1024; cp.n_batch = plain ? 128 : 1024;
    cp.n_ubatch = plain ? 128 : 1024; cp.n_seq_max = 1;
    cp.n_threads = threads; cp.n_threads_batch = threads; cp.offload_kqv = false; cp.op_offload = false;
    if (!plain) { cp.cb_eval = observe; cp.cb_eval_user_data = &tap; }
    llama_context * ctx = llama_init_from_model(model, cp); if (!ctx) return 4;
    std::ifstream in(argv[2]); std::ofstream index(out + "/index.jsonl");
    std::string line; int row = 0;
    while (std::getline(in, line)) {
        std::vector<llama_token> ids = parse_ids(line);
        if (ids.empty()) continue;
        tap.data.clear(); tap.width.clear();
        llama_memory_clear(llama_get_memory(ctx), true);
        // Request outputs for every token: otherwise the last layer is pruned to the output rows only.
        llama_batch batch = llama_batch_init((int) ids.size(), 0, 1);
        for (size_t i = 0; i < ids.size(); ++i) {
            batch.token[i] = ids[i]; batch.pos[i] = (llama_pos) i; batch.n_seq_id[i] = 1; batch.seq_id[i][0] = 0;
            batch.logits[i] = plain ? (i + 1 == ids.size()) : 1;
        }
        batch.n_tokens = (int) ids.size();
        const int rc = llama_decode(ctx, batch);
        llama_batch_free(batch);
        if (rc != 0) { std::fprintf(stderr, "decode failed on line %d\n", row); return 5; }
        std::ostringstream names;
        bool first = true;
        for (auto & kv : tap.data) {
            const std::string path = out + "/" + std::to_string(row) + "." + kv.first + ".f32";
            std::ofstream f(path, std::ios::binary);
            f.write((const char *) kv.second.data(), (std::streamsize) (kv.second.size() * sizeof(float)));
            names << (first ? "" : ",") << "\"" << kv.first << "\":" << tap.width[kv.first];
            first = false;
        }
        index << "{\"row\":" << row << ",\"n_tokens\":" << ids.size() << ",\"tensors\":{" << names.str() << "}}\n";
        index.flush();
        ++row;
    }
    llama_free(ctx); llama_model_free(model); llama_backend_free();
    std::printf("{\"rows\":%d}\n", row);
    return 0;
}
