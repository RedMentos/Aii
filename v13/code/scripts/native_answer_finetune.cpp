// WP-S6 rest: answer-only selective finetune with llama.cpp's ggml-opt (no Python, no torch). Isolated candidate next
// to native_select_finetune.cpp (unchanged, hash-bound in the tested-package manifests). Differences to that tool:
//   - the training file marks answer spans with the control bytes \x01 (start) and \x02 (end); only tokens inside a
//     span are predicted (loss), prompt tokens get label -1 = masked. Needs patches/ggml-lfm2-backward-b10964.patch:
//     negative labels leave a zero row in the one-hot label tensor (llama-context.cpp), and the stock cross-entropy
//     backward would still give such a row softmax as gradient (ggml-cpu/ops.cpp fix);
//   - each segment is tokenised on its own, so the prompt/answer boundary is exactly where generation starts;
//   - optional KL anchor: spans marked \x03 (start) .. \x04 (end) get soft labels = the base model's own next-token
//     distribution (top V13_KL_K, default 32, renormalised, times V13_KL_WEIGHT, default 1), computed with the
//     untouched weights in the same datapoint context before training (llama_opt_set_soft_labels from the patch);
//   - prints the number of supervised tokens next to the other TrainRunnerProof numbers.
// Datapoints: n_ctx tokens, stride n_ctx/2 (same layout as common_opt_dataset_init).
//   V13_TRAIN_TENSORS=blk.12.ffn_down ./native-answer-finetune -m master-f32.gguf -f train.txt -o out.gguf -c 256 -b 256 -ub 256 --epochs 4
#include "arg.h"
#include "common.h"
#include "log.h"
#include "llama.h"
#include "ggml.h"
#include "ggml-opt.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <clocale>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <sys/resource.h>

struct filter_ud { std::vector<std::string> keys; int64_t n_params = 0; int n_tensors = 0; };

static bool v13_filter(const struct ggml_tensor * t, void * ud) {
    auto * f = (filter_ud *) ud;
    if (t->type != GGML_TYPE_F32) return false;
    const std::string name = ggml_get_name(t);
    for (const auto & k : f->keys) {
        if (!k.empty() && name.find(k) != std::string::npos) { f->n_params += ggml_nelements(t); f->n_tensors++; return true; }
    }
    return false;
}

enum span_kind : char { PROMPT = 0, ANSWER = 1, ANCHOR = 2 };

// tokens of the whole stream + per token: prompt, answer span (\x01..\x02) or anchor span (\x03..\x04)
static bool tokenize_marked(llama_context * ctx, const std::string & text, std::vector<llama_token> & toks, std::vector<char> & kind) {
    size_t pos = 0; char cur = PROMPT; bool first = true;
    while (true) {
        const size_t next = text.find_first_of(std::string("\x01\x02\x03\x04", 4), pos);
        const std::string seg = text.substr(pos, next == std::string::npos ? std::string::npos : next - pos);
        if (!seg.empty() || first) {
            const auto t = common_tokenize(ctx, seg, /*add_special=*/ first, /*parse_special=*/ true);
            toks.insert(toks.end(), t.begin(), t.end()); kind.insert(kind.end(), t.size(), cur);
            first = false;
        }
        if (next == std::string::npos) return cur == PROMPT;  // an unterminated span is an error
        const char c = text[next];
        if      (c == '\x01' && cur == PROMPT) cur = ANSWER;
        else if (c == '\x02' && cur == ANSWER) cur = PROMPT;
        else if (c == '\x03' && cur == PROMPT) cur = ANCHOR;
        else if (c == '\x04' && cur == ANCHOR) cur = PROMPT;
        else return false;  // nested or unbalanced markers
        pos = next + 1;
    }
}

static double env_num(const char * name, double def) { const char * v = std::getenv(name); return v && *v ? std::atof(v) : def; }

int main(int argc, char ** argv) {
    std::setlocale(LC_NUMERIC, "C");
    common_params params;
    params.escape = false;
    common_init();
    if (!common_params_parse(argc, argv, params, LLAMA_EXAMPLE_FINETUNE)) return 1;
    params.load_mode = LLAMA_LOAD_MODE_NONE;  // writable weights
    params.cache_type_k = GGML_TYPE_F32;
    params.cache_type_v = GGML_TYPE_F32;

    filter_ud fud;
    const char * env = std::getenv("V13_TRAIN_TENSORS");
    if (!env || !*env) { LOG_ERR("V13_TRAIN_TENSORS is empty: refusing to train all weights\n"); return 2; }
    {
        std::string s(env), cur;
        for (char c : s) { if (c == ',') { fud.keys.push_back(cur); cur.clear(); } else cur += c; }
        fud.keys.push_back(cur);
    }

    llama_backend_init();
    llama_numa_init(params.numa);
    auto llama_init = common_init_from_params(params);
    auto * model = llama_init->model();
    auto * ctx   = llama_init->context();
    if (model == NULL) { LOG_ERR("unable to load model\n"); return 1; }

    std::vector<llama_token> tokens; std::vector<char> kind;
    if (!tokenize_marked(ctx, params.prompt, tokens, kind)) { LOG_ERR("unbalanced span markers (\\x01..\\x02, \\x03..\\x04)\n"); return 4; }
    const int64_t n_ctx = llama_n_ctx(ctx), stride = n_ctx / 2;
    if ((int64_t) tokens.size() < n_ctx + 1) { LOG_ERR("stream shorter than one datapoint\n"); return 5; }
    const int64_t ndata = ((int64_t) tokens.size() - n_ctx - 1) / stride;
    ggml_opt_dataset_t dataset = ggml_opt_dataset_init(GGML_TYPE_I32, GGML_TYPE_I32, n_ctx, n_ctx, ndata, /*ndata_shard =*/ 1);
    auto * data   = (llama_token *) ggml_opt_dataset_data(dataset)->data;
    auto * labels = (llama_token *) ggml_opt_dataset_labels(dataset)->data;
    const int32_t kl_k = (int32_t) env_num("V13_KL_K", 32); const float kl_w = (float) env_num("V13_KL_WEIGHT", 1.0);
    const int32_t n_vocab = llama_vocab_n_tokens(llama_model_get_vocab(model));
    if (kl_k > n_vocab) { LOG_ERR("V13_KL_K larger than the vocabulary\n"); return 8; }
    std::vector<int32_t> soft_ids; std::vector<float> soft_p; std::vector<int32_t> order(n_vocab); std::vector<float> row(std::max(kl_k, 1));
    llama_batch batch = llama_batch_init(n_ctx, 0, 1);
    int64_t n_supervised = 0, n_soft = 0; double soft_mass = 0;
    for (int64_t i = 0; i < ndata; ++i) {
        bool any_anchor = false;
        for (int64_t j = 0; j < n_ctx; ++j) {
            const int64_t k = i*stride + j;
            data[i*n_ctx + j]   = tokens[k];
            labels[i*n_ctx + j] = kind[k + 1] == ANSWER ? tokens[k + 1] : -1;
            n_supervised += kind[k + 1] == ANSWER;
            any_anchor |= kind[k + 1] == ANCHOR;
        }
        if (!any_anchor || kl_k <= 0 || kl_w <= 0) continue;
        // base distribution in the same datapoint context the optimizer will see (memory cleared, positions 0..n_ctx-1)
        llama_memory_clear(llama_get_memory(ctx), true);
        common_batch_clear(batch);
        for (int64_t j = 0; j < n_ctx; ++j) {
            common_batch_add(batch, tokens[i*stride + j], (llama_pos) j, {0}, kind[i*stride + j + 1] == ANCHOR);
        }
        if (llama_decode(ctx, batch) != 0) { LOG_ERR("base decode failed\n"); return 7; }
        for (int64_t j = 0; j < n_ctx; ++j) {
            if (kind[i*stride + j + 1] != ANCHOR) continue;
            const float * lg = llama_get_logits_ith(ctx, (int32_t) j);
            for (int32_t v = 0; v < n_vocab; ++v) order[v] = v;
            std::partial_sort(order.begin(), order.begin() + kl_k, order.end(), [&](int32_t x, int32_t y) { return lg[x] > lg[y]; });
            double z = 0, ztop = 0; const float mx = lg[order[0]];
            for (int32_t v = 0; v < n_vocab; ++v) z += std::exp((double) lg[v] - mx);
            for (int32_t t = 0; t < kl_k; ++t) ztop += row[t] = (float) std::exp((double) lg[order[t]] - mx);
            soft_mass += ztop / z;
            for (int32_t t = 0; t < kl_k; ++t) { soft_ids.push_back(order[t]); soft_p.push_back((float) (kl_w * row[t] / ztop)); }
            labels[i*n_ctx + j] = (llama_token) (-2 - n_soft); n_soft++;
        }
    }
    llama_batch_free(batch);
    llama_memory_clear(llama_get_memory(ctx), true);
    if (n_supervised == 0) { LOG_ERR("no answer span inside the datapoints\n"); return 6; }
    struct lr_opt & lr = params.lr;

    struct llama_opt_params lopt_params{
        /*n_ctx_train     =*/0,
        /*param_filter    =*/v13_filter,
        /*param_filter_ud =*/&fud,
        /*get_opt_pars    =*/common_opt_lr_pars,
        /*get_opt_pars_ud =*/&params.lr,
        /*optimizer_type  =*/params.optimizer,
    };
    auto t0 = std::chrono::steady_clock::now();
    llama_opt_init(ctx, model, lopt_params);
    llama_opt_set_soft_labels(ctx, soft_ids.data(), soft_p.data(), kl_k, n_soft);
    if (fud.n_tensors == 0) { LOG_ERR("no F32 tensor matched V13_TRAIN_TENSORS\n"); return 3; }
    const int64_t idata_split = ggml_opt_dataset_ndata(dataset) * (1.0f - params.val_split);
    ggml_opt_result_t result_train = ggml_opt_result_init();
    ggml_opt_result_t result_eval  = ggml_opt_result_init();
    double last_loss = 0, last_unc = 0;
    for (lr.epoch = 0; lr.epoch < lr.epochs; ++lr.epoch) {
        llama_opt_epoch(ctx, dataset, result_train, result_eval, idata_split,
                        ggml_opt_epoch_callback_progress_bar, ggml_opt_epoch_callback_progress_bar);
        fprintf(stderr, "\n");
        // ggml averages the loss over all n_ctx rows; masked rows add 0, so this is not a per-answer-token loss
        ggml_opt_result_loss(result_train, &last_loss, &last_unc);
        fprintf(stderr, "V13_EPOCH {\"epoch\":%d,\"train_loss_all_rows\":%.6f}\n", lr.epoch, last_loss);
        ggml_opt_result_reset(result_train);
        ggml_opt_result_reset(result_eval);
    }
    ggml_opt_result_free(result_train);
    ggml_opt_result_free(result_eval);
    const double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    llama_model_save_to_file(model, params.out_file.c_str());
    struct rusage ru; getrusage(RUSAGE_SELF, &ru);
    printf("V13_RESULT {\"trainable_tensors\":%d,\"trainable_parameter_count\":%lld,\"tokens\":%zu,\"datapoints\":%lld,\"supervised_label_slots\":%lld,\"kl_rows\":%lld,\"kl_k\":%d,\"kl_weight\":%.3f,\"kl_topk_mass\":%.4f,\"epochs\":%d,\"seconds\":%.2f,\"peak_rss_mb\":%.1f,\"final_train_loss_all_rows\":%.6f,\"out\":\"%s\"}\n",
           fud.n_tensors, (long long) fud.n_params, tokens.size(), (long long) ndata, (long long) n_supervised, (long long) n_soft, kl_k, kl_w,
           n_soft ? soft_mass / n_soft : 0.0, lr.epochs, secs,
           ru.ru_maxrss / 1024.0, last_loss, params.out_file.c_str());
    ggml_opt_dataset_free(dataset);
    llama_backend_free();
    return 0;
}
