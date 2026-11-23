// WP-S6 on-device path: selective-tensor finetune with llama.cpp's own ggml-opt (no Python, no torch).
// Based on llama.cpp examples/training/finetune.cpp. Differences:
//   - only tensors whose name contains one of V13_TRAIN_TENSORS (comma list) get gradients (param_filter),
//     everything else stays frozen -> small optimizer state, Sparse-Memory-Finetuning-like locality;
//   - prints a JSON line with trainable parameter count, seconds and peak RSS for the TrainRunnerProof.
// Model must be an FP32 master GGUF (finetune needs writable FP32 weights). Afterwards llama-quantize can keep the
// trained tensors in F16/F32 via --tensor-type and quantize the rest (body_training.py requantizer contract).
// Build: see scripts/build_native_finetune.sh. Usage:
//   V13_TRAIN_TENSORS=blk.11.ffn_down,blk.12.ffn_down ./native-select-finetune -m master-f32.gguf -f train.txt -o out.gguf -c 256 -b 256 -ub 256 --epochs 4
#include "arg.h"
#include "common.h"
#include "log.h"
#include "llama.h"
#include "ggml.h"

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

    std::vector<llama_token> tokens = common_tokenize(ctx, params.prompt, true, /*parse_special=*/ true);  // chat-template markers must be control tokens
    ggml_opt_dataset_t dataset = common_opt_dataset_init(ctx, tokens, llama_n_ctx(ctx) / 2);
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
        ggml_opt_result_loss(result_train, &last_loss, &last_unc);
        fprintf(stderr, "V13_EPOCH {\"epoch\":%d,\"train_loss\":%.6f}\n", lr.epoch, last_loss);
        ggml_opt_result_reset(result_train);
        ggml_opt_result_reset(result_eval);
    }
    ggml_opt_result_free(result_train);
    ggml_opt_result_free(result_eval);
    const double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    llama_model_save_to_file(model, params.out_file.c_str());
    struct rusage ru; getrusage(RUSAGE_SELF, &ru);
    printf("V13_RESULT {\"trainable_tensors\":%d,\"trainable_parameter_count\":%lld,\"tokens\":%zu,\"epochs\":%d,\"seconds\":%.2f,\"peak_rss_mb\":%.1f,\"final_train_loss\":%.6f,\"out\":\"%s\"}\n",
           fud.n_tensors, (long long) fud.n_params, tokens.size(), lr.epochs, secs, ru.ru_maxrss / 1024.0, last_loss, params.out_file.c_str());
    llama_backend_free();
    return 0;
}
