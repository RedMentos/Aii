// WP-S6 rest: answer-only selective finetune with llama.cpp's ggml-opt (no Python, no torch). Isolated candidate next
// to native_select_finetune.cpp (unchanged, hash-bound in the tested-package manifests). Differences to that tool:
//   - the training file marks answer spans with the control bytes \x01 (start) and \x02 (end); only tokens inside a
//     span are predicted (loss), prompt tokens get label -1 = masked. Needs patches/ggml-lfm2-backward-b10964.patch:
//     negative labels leave a zero row in the one-hot label tensor (llama-context.cpp), and the stock cross-entropy
//     backward would still give such a row softmax as gradient (ggml-cpu/ops.cpp fix);
//   - each segment is tokenised on its own, so the prompt/answer boundary is exactly where generation starts;
//   - prints the number of supervised tokens next to the other TrainRunnerProof numbers.
// Datapoints: n_ctx tokens, stride n_ctx/2 (same layout as common_opt_dataset_init).
//   V13_TRAIN_TENSORS=blk.12.ffn_down ./native-answer-finetune -m master-f32.gguf -f train.txt -o out.gguf -c 256 -b 256 -ub 256 --epochs 4
#include "arg.h"
#include "common.h"
#include "log.h"
#include "llama.h"
#include "ggml.h"
#include "ggml-opt.h"

#include <chrono>
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

// tokens of the whole stream + per token: is it inside an answer span
static bool tokenize_marked(llama_context * ctx, const std::string & text, std::vector<llama_token> & toks, std::vector<char> & answer) {
    size_t pos = 0; bool in_answer = false, first = true;
    while (pos <= text.size()) {
        const size_t next = text.find(in_answer ? '\x02' : '\x01', pos);
        const std::string seg = text.substr(pos, next == std::string::npos ? std::string::npos : next - pos);
        if (!seg.empty() || first) {
            const auto t = common_tokenize(ctx, seg, /*add_special=*/ first, /*parse_special=*/ true);
            toks.insert(toks.end(), t.begin(), t.end()); answer.insert(answer.end(), t.size(), in_answer ? 1 : 0);
            first = false;
        }
        if (next == std::string::npos) { if (in_answer) return false; break; }  // unterminated answer span
        pos = next + 1; in_answer = !in_answer;
    }
    return true;
}

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

    std::vector<llama_token> tokens; std::vector<char> answer;
    if (!tokenize_marked(ctx, params.prompt, tokens, answer)) { LOG_ERR("unterminated answer span (\\x01 without \\x02)\n"); return 4; }
    const int64_t n_ctx = llama_n_ctx(ctx), stride = n_ctx / 2;
    if ((int64_t) tokens.size() < n_ctx + 1) { LOG_ERR("stream shorter than one datapoint\n"); return 5; }
    const int64_t ndata = ((int64_t) tokens.size() - n_ctx - 1) / stride;
    ggml_opt_dataset_t dataset = ggml_opt_dataset_init(GGML_TYPE_I32, GGML_TYPE_I32, n_ctx, n_ctx, ndata, /*ndata_shard =*/ 1);
    auto * data   = (llama_token *) ggml_opt_dataset_data(dataset)->data;
    auto * labels = (llama_token *) ggml_opt_dataset_labels(dataset)->data;
    int64_t n_supervised = 0;
    for (int64_t i = 0; i < ndata; ++i) {
        for (int64_t j = 0; j < n_ctx; ++j) {
            const int64_t k = i*stride + j;
            data[i*n_ctx + j]   = tokens[k];
            labels[i*n_ctx + j] = answer[k + 1] ? tokens[k + 1] : -1;
            n_supervised += answer[k + 1];
        }
    }
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
    printf("V13_RESULT {\"trainable_tensors\":%d,\"trainable_parameter_count\":%lld,\"tokens\":%zu,\"datapoints\":%lld,\"supervised_label_slots\":%lld,\"epochs\":%d,\"seconds\":%.2f,\"peak_rss_mb\":%.1f,\"final_train_loss_all_rows\":%.6f,\"out\":\"%s\"}\n",
           fud.n_tensors, (long long) fud.n_params, tokens.size(), (long long) ndata, (long long) n_supervised, lr.epochs, secs,
           ru.ru_maxrss / 1024.0, last_loss, params.out_file.c_str());
    ggml_opt_dataset_free(dataset);
    llama_backend_free();
    return 0;
}
