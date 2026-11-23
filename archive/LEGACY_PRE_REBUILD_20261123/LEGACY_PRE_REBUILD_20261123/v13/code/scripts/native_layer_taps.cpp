// Read-only native layer taps for the action-JEPA round 4 diagnostic; no weights or outputs are changed.
// For each input line (UTF-8 text, '\n'-free, JSON-escaped by the caller is not needed: raw lines),
// one forward pass over the raw text (add_special=true, parse_special=false) is run and the cb_eval
// hook copies the residual stream "l_out-<L>" for every requested layer L. Written per text and layer:
// last-token vector and mean-over-tokens vector, float32, row-major, to OUT.bin; OUT.json describes it.
//   native_layer_taps MODEL.gguf LAYERS(comma) INPUT.txt OUT THREADS
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

struct Taps {
    std::map<std::string, int> wanted;  // tensor name -> layer
    std::map<int, std::vector<float>> got;  // layer -> [n_embd * n_tokens]
    int n_embd = 0;
};

static bool hook(struct ggml_tensor * t, bool ask, void * user) {
    auto * taps = (Taps *) user;
    auto it = taps->wanted.find(ggml_get_name(t));
    if (it == taps->wanted.end()) return ask ? false : true;
    if (ask) return true;
    if (t->type != GGML_TYPE_F32 || ggml_n_dims(t) > 2) return true;
    std::vector<float> & v = taps->got[it->second];
    v.resize(ggml_nelements(t));
    ggml_backend_tensor_get(t, v.data(), 0, ggml_nbytes(t));
    taps->n_embd = (int) t->ne[0];
    return true;
}

int main(int argc, char ** argv) {
    if (argc != 6) { std::fprintf(stderr, "usage: %s MODEL LAYERS INPUT OUT THREADS\n", argv[0]); return 2; }
    std::vector<int> layers;
    { std::stringstream ss(argv[2]); std::string s; while (std::getline(ss, s, ',')) layers.push_back(std::stoi(s)); }
    std::vector<std::string> texts;
    { std::ifstream in(argv[3]); std::string line; while (std::getline(in, line)) texts.push_back(line); }
    const int threads = std::stoi(argv[5]);
    Taps taps;
    for (int l : layers) taps.wanted["l_out-" + std::to_string(l)] = l;
    llama_backend_init();
    // Release builds with dynamically loaded CPU backends (GGML_BACKEND_DL, e.g. the pinned b10964 binaries)
    // register nothing until asked; static builds already have their backend, so this changes nothing there.
    // V13_GGML_BACKEND_DIR names the runner's library directory; otherwise ggml searches its default places.
    if (ggml_backend_reg_count() == 0) {
        const char * dir = std::getenv("V13_GGML_BACKEND_DIR");
        if (dir && *dir) ggml_backend_load_all_from_path(dir); else ggml_backend_load_all();
    }
    auto mp = llama_model_default_params(); mp.n_gpu_layers = 0;
    llama_model * model = llama_model_load_from_file(argv[1], mp); if (!model) return 3;
    const llama_vocab * vocab = llama_model_get_vocab(model);
    auto cp = llama_context_default_params(); cp.n_ctx = 512; cp.n_batch = 512; cp.n_ubatch = 512;  // texts are short; 2048 reserved a 1.9 GiB compute buffer
    cp.n_threads = threads; cp.n_threads_batch = threads; cp.cb_eval = hook; cp.cb_eval_user_data = &taps;
    llama_context * ctx = llama_init_from_model(model, cp); if (!ctx) return 4;
    FILE * out = std::fopen((std::string(argv[4]) + ".bin").c_str(), "wb"); if (!out) return 5;
    std::vector<int> token_counts;
    for (const std::string & text : texts) {
        std::vector<llama_token> toks(text.size() + 16);
        int n = llama_tokenize(vocab, text.c_str(), (int) text.size(), toks.data(), (int) toks.size(), true, false);
        if (n < 0) { toks.resize(-n); n = llama_tokenize(vocab, text.c_str(), (int) text.size(), toks.data(), (int) toks.size(), true, false); }
        if (n <= 0) return 6;
        toks.resize(n);
        llama_memory_clear(llama_get_memory(ctx), true);
        taps.got.clear();
        if (llama_decode(ctx, llama_batch_get_one(toks.data(), n)) != 0) return 7;
        for (int l : layers) {
            auto it = taps.got.find(l);
            if (it == taps.got.end() || taps.n_embd <= 0 || (int) it->second.size() < taps.n_embd) return 8;
            const int d = taps.n_embd, rows = (int) it->second.size() / d;
            std::vector<float> last(it->second.end() - d, it->second.end()), mean(d, 0.f);
            for (int r = 0; r < rows; ++r) for (int k = 0; k < d; ++k) mean[k] += it->second[(size_t) r * d + k] / rows;
            std::fwrite(last.data(), sizeof(float), d, out);
            std::fwrite(mean.data(), sizeof(float), d, out);
        }
        token_counts.push_back(n);
    }
    std::fclose(out);
    std::ofstream meta(std::string(argv[4]) + ".json");
    meta << "{\"schema\":\"v13-native-layer-taps-v1\",\"texts\":" << texts.size() << ",\"n_embd\":" << taps.n_embd
         << ",\"layers\":[";
    for (size_t i = 0; i < layers.size(); ++i) meta << (i ? "," : "") << layers[i];
    meta << "],\"order\":\"text-major, then layer, then [last_token, mean_tokens]\",\"dtype\":\"float32\",\"token_counts\":[";
    for (size_t i = 0; i < token_counts.size(); ++i) meta << (i ? "," : "") << token_counts[i];
    meta << "],\"n_layer\":" << llama_model_n_layer(model) << ",\"receiver_authority\":0}\n";
    llama_free(ctx); llama_model_free(model); llama_backend_free();
    return 0;
}
