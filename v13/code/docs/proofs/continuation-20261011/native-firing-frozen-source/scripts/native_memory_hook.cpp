// WP-S3 native path: serve the keyed sparse memory (v13/sparse_memory.py, exported by export_native) inside llama.cpp
// without Python. A cb_eval hook captures the FFN input of the memory layer (RMS-normed residual, ggml MUL node named
// "*ffn_norm-L" or, in newer graphs, "*ffn_out-L") and adds the gated memory output to "*l_out-L" before layer L+1 reads it:
//   qn = normalize(x - mu); c_s = qn . key_s; g_s = sigmoid((c_s - theta_s)/tau) * [entity token of slot s in context]
//   l_out += scale * sum_{s in top-k} g_s * value_s
// Equivalent to torch's ffn(x)+memory(x) because the block output is residual + ffn_out. CPU only (-ngl 0), greedy.
// Usage: native-memory-hook <model.gguf> <memory.bin> <prompts.jsonl> [threads]
//   prompts.jsonl: one JSON string per line, already chat-templated; prints one JSON object per prompt.
#include "llama.h"
#include "ggml.h"
#include "ggml-backend.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include "v13_memory_hook.h"

static std::string json_escape(const std::string & s) {
    std::ostringstream o; for (unsigned char ch : s) { if (ch == '"' || ch == '\\') o << '\\' << ch; else if (ch == '\n') o << "\\n"; else if (ch < 0x20) { char b[8]; std::snprintf(b, 8, "\\u%04x", ch); o << b; } else o << ch; }
    return o.str();
}
static std::string json_unquote(const std::string & line) {  // minimal: one JSON string per line
    std::string s; bool esc = false; size_t i = line.find('"'); if (i == std::string::npos) return s;
    for (++i; i < line.size(); ++i) { char ch = line[i];
        if (esc) { s += ch == 'n' ? '\n' : ch == 't' ? '\t' : ch; esc = false; } else if (ch == '\\') esc = true; else if (ch == '"') break; else s += ch; }
    return s;
}

int main(int argc, char ** argv) {
    if (argc < 4) { std::fprintf(stderr, "usage: %s model.gguf memory.bin prompts.jsonl [threads] [max_new]\n", argv[0]); return 1; }
    Memory mem; if (!load_memory(argv[2], mem)) { std::fprintf(stderr, "bad memory file\n"); return 2; }
    mem.audit = std::getenv("V13_MEMORY_AUDIT") != nullptr;
    const int threads = argc > 4 ? std::atoi(argv[4]) : 4, max_new = argc > 5 ? std::atoi(argv[5]) : 32;
    llama_backend_init();
    auto mp = llama_model_default_params(); mp.n_gpu_layers = 0;
    llama_model * model = llama_model_load_from_file(argv[1], mp); if (!model) return 3;
    const llama_vocab * vocab = llama_model_get_vocab(model);
    auto cp = llama_context_default_params(); cp.n_ctx = 1024; cp.n_batch = 512; cp.n_ubatch = 512; cp.n_threads = threads; cp.n_threads_batch = threads;
    cp.cb_eval = hook; cp.cb_eval_user_data = &mem;
    llama_context * ctx = llama_init_from_model(model, cp); if (!ctx) return 4;
    llama_sampler * smpl = llama_sampler_init_greedy();
    std::ifstream pf(argv[3]); std::string line;
    while (std::getline(pf, line)) {
        if (line.empty()) continue; const std::string prompt = json_unquote(line);
        std::vector<llama_token> toks(prompt.size() + 16);
        int n = llama_tokenize(vocab, prompt.c_str(), (int) prompt.size(), toks.data(), (int) toks.size(), false, true);
        if (n < 0) { toks.resize(-n); n = llama_tokenize(vocab, prompt.c_str(), (int) prompt.size(), toks.data(), (int) toks.size(), false, true); }
        toks.resize(n);
        llama_memory_clear(llama_get_memory(ctx), true); mem.ctx = std::set<int32_t>(toks.begin(), toks.end()); mem.fired = 0;
        v13_audit_begin(mem);
        std::string out; llama_batch batch = llama_batch_get_one(toks.data(), (int) toks.size()); llama_token tok;
        for (int i = 0; i < max_new; ++i) {
            if (llama_decode(ctx, batch) != 0) break;
            tok = llama_sampler_sample(smpl, ctx, -1); if (llama_vocab_is_eog(vocab, tok)) break;
            char buf[256]; int k = llama_token_to_piece(vocab, tok, buf, sizeof buf, 0, false); if (k > 0) out.append(buf, k);
            mem.ctx.insert(tok); batch = llama_batch_get_one(&tok, 1);
        }
        std::printf("{\"prompt\":\"%s\",\"text\":\"%s\",\"memory_fired\":%ld}\n", json_escape(prompt).c_str(), json_escape(out).c_str(), mem.fired); std::fflush(stdout);
    }
    llama_sampler_free(smpl); llama_free(ctx); llama_model_free(model); llama_backend_free();
    return 0;
}
