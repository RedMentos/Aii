// Portable read-only BodyPort parity worker; not a production decoder replacement.
// Build against exact llama.cpp b10964 public headers and release libraries.
// No training, receiver injection, artifact activation or external action authority.
#include "llama.h"
#include "ggml.h"
#include "ggml-backend.h"
#include "nlohmann/json.hpp"
extern "C" {
#include "sha256.h"
}
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstring>
#include <dlfcn.h>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include <unistd.h>
using json = nlohmann::json;
using Clock = std::chrono::steady_clock;
static volatile std::sig_atomic_t interrupted = 0;
static void signal_handler(int) { interrupted = 1; }
static std::string sha_file(const std::string & path) {
    std::ifstream f(path, std::ios::binary); if (!f) throw std::runtime_error("Cannot hash " + path);
    sha256_t state; sha256_init(&state); char buf[65536];
    while (f) { f.read(buf, sizeof(buf)); auto n=f.gcount(); if(n>0) sha256_update(&state,reinterpret_cast<unsigned char*>(buf),size_t(n)); }
    if (!f.eof()) throw std::runtime_error("Hash read failed: " + path);
    unsigned char digest[32]; sha256_final(&state,digest); std::ostringstream s;
    for (unsigned char v:digest) { s<<std::hex<<std::setw(2)<<std::setfill('0')<<int(v); }
    return s.str();
}
static json library_identity(const void * function) {
    Dl_info d{}; if (!dladdr(function,&d) || !d.dli_fname) throw std::runtime_error("Cannot resolve actual loaded library");
    return {{"path",d.dli_fname},{"sha256",sha_file(d.dli_fname)}};
}
struct Capture {
    int dimension=0, decode_id=0, norm_count=0, output_count=0;
    bool active=false, embedding_mode=false; std::string error; std::vector<float> hidden;
    json records=json::array(); Clock::time_point deadline;
};
static bool abort_compute(void * opaque) {
    auto & c=*static_cast<Capture*>(opaque);
    return interrupted || Clock::now()>=c.deadline || !c.error.empty();
}
static bool observe(ggml_tensor * tensor,bool ask,void * opaque) noexcept {
    auto & c=*static_cast<Capture*>(opaque);
    // Pooling NONE aliases the same native tensor, then renames it in build_pooling.
    bool norm=std::strcmp(ggml_get_name(tensor),"result_norm")==0 ||
              (c.embedding_mode && std::strcmp(ggml_get_name(tensor),"result_embd_pooled")==0);
    bool output=std::strcmp(ggml_get_name(tensor),"result_output")==0;
    if (ask) return c.active && (norm||output) && tensor->ne[1]>0;
    try {
        if (!c.active || (!norm&&!output)) throw std::runtime_error("Unexpected callback node");
        if (c.records.size()>=64) throw std::runtime_error("Bounded callback record limit");
        json r={{"decode_id",c.decode_id},{"node",ggml_get_name(tensor)},{"type",ggml_type_name(tensor->type)},
          {"shape",{tensor->ne[0],tensor->ne[1],tensor->ne[2],tensor->ne[3]}},
          {"strides_bytes",{tensor->nb[0],tensor->nb[1],tensor->nb[2],tensor->nb[3]}}};
        if (tensor->type!=GGML_TYPE_F32 || tensor->ne[1]<1 || tensor->ne[1]>512 || tensor->ne[2]!=1 || tensor->ne[3]!=1 || tensor->nb[0]!=sizeof(float)) throw std::runtime_error("Unexpected native tensor shape/type/stride");
        if (norm) {
            if (tensor->ne[0]!=c.dimension || tensor->nb[1]<size_t(c.dimension)*sizeof(float)) throw std::runtime_error("Native result_norm dimension mismatch");
            ++c.norm_count; c.hidden.resize(c.dimension);
            ggml_backend_tensor_get(tensor,c.hidden.data(),size_t(tensor->ne[1]-1)*tensor->nb[1],size_t(c.dimension)*sizeof(float));
            double sum=0.; for (float v:c.hidden) {if(!std::isfinite(v)) throw std::runtime_error("Nonfinite native hidden state");sum+=double(v)*v;}
            if(sum<=1e-20) throw std::runtime_error("Native hidden state is empty");
            r["last_output_squared_norm"]=sum;
        } else ++c.output_count;
        c.records.push_back(r); return true;
    } catch(const std::exception & e) { c.error=e.what(); return false; }
}
static json logits_result(llama_context * ctx,int vocabulary) {
    auto * p=llama_get_logits_ith(ctx,-1);if(!p) throw std::runtime_error("No actual last logits");
    std::vector<float> values(p,p+vocabulary); double maximum=-INFINITY;
    for(float v:values) {if(!std::isfinite(v)) throw std::runtime_error("Nonfinite actual logits");maximum=std::max(maximum,double(v));}
    std::vector<double> probabilities(vocabulary);double sum=0.;
    for(int i=0;i<vocabulary;++i){probabilities[i]=std::exp(double(values[i])-maximum);sum+=probabilities[i];}
    if(!std::isfinite(sum)||sum<=0)throw std::runtime_error("Invalid actual vocabulary mass");
    for(double & v:probabilities)v/=sum;
    int greedy=int(std::max_element(values.begin(),values.end())-values.begin());
    return {{"logits",values},{"probabilities",probabilities},{"vocabulary_size",vocabulary},{"greedy_token_id",greedy},{"logsumexp",maximum+std::log(sum)}};
}
static void save_json(const std::string & path,const json & data) {
    std::ofstream f(path,std::ios::binary|std::ios::trunc);if(!f)throw std::runtime_error("Cannot open output");f<<data.dump(2,' ',false,json::error_handler_t::replace)<<'\n';f.flush();if(!f)throw std::runtime_error("Output write failed");
}
int main(int argc,char ** argv) {
    json report={{"schema","V13_ISOLATED_NATIVE_LIVE_PREFILL_PORT_V1"},{"implemented_in_production",false},{"train_authority",0},{"receiver_authority",0},{"native_body_parameters_modified",0},{"pid",getpid()}};
    std::string out;
    try {
        std::map<std::string,std::string> a;
        for(int i=1;i<argc;i+=2){if(i+1>=argc||std::string(argv[i]).rfind("--",0)!=0||a.count(argv[i]))throw std::runtime_error("Expected unique --key value arguments");a[argv[i]]=argv[i+1];}
        const std::vector<std::string> allowed={"--model","--tokens","--output","--mode","--n-batch","--n-ubatch","--ctx","--threads","--continue","--seconds","--model-sha256","--lib-sha256","--backend-pins"};
        for(auto & item:a)if(std::find(allowed.begin(),allowed.end(),item.first)==allowed.end())throw std::runtime_error("Unknown argument "+item.first);
        for(auto key:{"--model","--tokens","--output","--model-sha256","--lib-sha256","--backend-pins"})if(!a.count(key))throw std::runtime_error(std::string("Missing ")+key);
        out=a.at("--output");auto mode=a.count("--mode")?a.at("--mode"):"live";
        if(mode!="live"&&mode!="baseline"&&mode!="embedding-counter")throw std::runtime_error("Mode must be live/baseline/embedding-counter");
        auto number=[&](const char * key,int fallback,int lo,int hi){int n=fallback;if(a.count(key)){size_t used=0;n=std::stoi(a.at(key),&used);if(used!=a.at(key).size())throw std::runtime_error("Invalid integer");}if(n<lo||n>hi)throw std::runtime_error(std::string("Bound exceeded: ")+key);return n;};
        int batch_size=number("--n-batch",128,1,512),ubatch=number("--n-ubatch",128,1,512),context=number("--ctx",2048,32,4096),threads=number("--threads",2,1,8),continuations=number("--continue",0,0,8),seconds=number("--seconds",90,1,120);
        if(ubatch>batch_size)throw std::runtime_error("Physical batch exceeds logical batch");
        std::ifstream input(a.at("--tokens"));json source;input>>source;if(!input||!source.is_object()||!source.contains("token_ids")||!source["token_ids"].is_array())throw std::runtime_error("Actual token_ids input required");
        if(source["token_ids"].empty()||source["token_ids"].size()>512||source["token_ids"].size()+continuations+1>size_t(context))throw std::runtime_error("Input token/context bounds exceeded");
        std::vector<llama_token> tokens;for(auto & v:source["token_ids"]){if(!v.is_number_integer()||v.is_boolean())throw std::runtime_error("Exact integer token ID required");int64_t n=v.get<int64_t>();if(n<0||n>INT32_MAX)throw std::runtime_error("Token ID out of range");tokens.push_back(llama_token(n));}
        report["mode"]=mode;report["token_ids"]=tokens;report["input_file_sha256"]=sha_file(a.at("--tokens"));
        report["model"]={{"path",a.at("--model")},{"sha256",sha_file(a.at("--model"))}};
        report["loaded_llama_library"]=library_identity(reinterpret_cast<const void*>(&llama_decode));
        report["loaded_ggml_base_library"]=library_identity(reinterpret_cast<const void*>(&ggml_backend_tensor_get));
        report["loaded_ggml_library"]=library_identity(reinterpret_cast<const void*>(&ggml_backend_load_all));
        if(report["model"]["sha256"]!=a.at("--model-sha256")||report["loaded_llama_library"]["sha256"]!=a.at("--lib-sha256"))throw std::runtime_error("Actual model/library hash does not match provided pin");
        report["configuration"]={{"context_tokens",context},{"n_batch",batch_size},{"n_ubatch",ubatch},{"threads",threads},{"embeddings",mode=="embedding-counter"},{"attention","MODEL_DEFAULT_UNSPECIFIED"},{"pooling","NONE"},{"continuation_steps",continuations},{"deadline_seconds",seconds}};
        std::signal(SIGINT,signal_handler);std::signal(SIGTERM,signal_handler);
        auto started=Clock::now();Capture capture;capture.embedding_mode=mode=="embedding-counter";capture.deadline=started+std::chrono::seconds(seconds);
        std::string backend_directory=report["loaded_ggml_library"]["path"].get<std::string>();
        backend_directory=backend_directory.substr(0,backend_directory.find_last_of('/'));
        ggml_backend_load_all_from_path(backend_directory.c_str());
        if(ggml_backend_reg_count()==0)throw std::runtime_error("No backend registered from exact loaded library directory");
        report["backend_directory"]=backend_directory;
        report["backend_registry"]=json::array();
        for(size_t i=0;i<ggml_backend_reg_count();++i)report["backend_registry"].push_back(ggml_backend_reg_name(ggml_backend_reg_get(i)));
        std::ifstream maps("/proc/self/maps");std::string map_line;std::set<std::string> backend_paths;
        while(std::getline(maps,map_line)){auto slash=map_line.find('/');if(slash!=std::string::npos){auto path=map_line.substr(slash);if(path.find("/libggml-cpu")!=std::string::npos)backend_paths.insert(path);}}
        report["loaded_cpu_backend_libraries"]=json::array();
        for(auto & path:backend_paths)report["loaded_cpu_backend_libraries"].push_back({{"path",path},{"sha256",sha_file(path)}});
        std::ifstream pin_input(a.at("--backend-pins"));json pins;pin_input>>pins;
        if(!pin_input || !pins.is_object() || !pins.contains("libraries") || !pins["libraries"].is_object())throw std::runtime_error("Actual library/backend pins required");
        auto verify_loaded=[&](const json & identity){
            const auto path=identity.at("path").get<std::string>();char actual_path[4096];
            if(!realpath(path.c_str(),actual_path))throw std::runtime_error("Cannot resolve loaded library path");
            const std::string key(actual_path);
            if(!pins["libraries"].contains(key)||pins["libraries"].at(key)!=identity.at("sha256"))throw std::runtime_error("Loaded library/backend differs from verified build manifest: "+key);
        };
        for(auto key:{"loaded_llama_library","loaded_ggml_base_library","loaded_ggml_library"})verify_loaded(report.at(key));
        if(report["loaded_cpu_backend_libraries"].empty())throw std::runtime_error("No actual loaded CPU backend library");
        for(const auto & identity:report["loaded_cpu_backend_libraries"])verify_loaded(identity);
        report["backend_pins_sha256"]=sha_file(a.at("--backend-pins"));
        report["all_loaded_libraries_verified"]=true;
        llama_backend_init();
        auto mp=llama_model_default_params();mp.n_gpu_layers=0;
        std::unique_ptr<llama_model,decltype(&llama_model_free)> model(llama_model_load_from_file(a.at("--model").c_str(),mp),llama_model_free);if(!model)throw std::runtime_error("Actual model load failed");
        capture.dimension=llama_model_n_embd_out(model.get());int vocabulary=llama_vocab_n_tokens(llama_model_get_vocab(model.get()));
        if(capture.dimension!=1024||vocabulary!=65536)throw std::runtime_error("This proof requires pinned 1024D/65536-vocabulary C3");
        for(auto t:tokens)if(t>=vocabulary)throw std::runtime_error("Input token outside actual vocabulary");
        auto cp=llama_context_default_params();cp.n_ctx=context;cp.n_batch=batch_size;cp.n_ubatch=ubatch;cp.n_seq_max=1;cp.n_threads=threads;cp.n_threads_batch=threads;cp.embeddings=mode=="embedding-counter";cp.pooling_type=LLAMA_POOLING_TYPE_NONE;cp.attention_type=LLAMA_ATTENTION_TYPE_UNSPECIFIED;cp.offload_kqv=false;cp.op_offload=false;cp.abort_callback=abort_compute;cp.abort_callback_data=&capture;
        if(mode!="baseline"){cp.cb_eval=observe;cp.cb_eval_user_data=&capture;}
        std::unique_ptr<llama_context,decltype(&llama_free)> ctx(llama_init_from_model(model.get(),cp),llama_free);if(!ctx)throw std::runtime_error("Actual context creation failed");
        report["actual_context"]={{"n_batch",llama_n_batch(ctx.get())},{"n_ubatch",llama_n_ubatch(ctx.get())},{"embedding_dimension",capture.dimension},{"vocabulary_size",vocabulary}};
        capture.active=true;auto b=llama_batch_init(batch_size,0,1);
        try {
            report["decode_calls"]=json::array();
            for(size_t offset=0;offset<tokens.size();offset+=batch_size){
                b.n_tokens=std::min<size_t>(batch_size,tokens.size()-offset);
                for(int i=0;i<b.n_tokens;++i){b.token[i]=tokens[offset+i];b.pos[i]=offset+i;b.n_seq_id[i]=1;b.seq_id[i][0]=0;b.logits[i]=mode=="embedding-counter"||offset+i+1==tokens.size();}
                ++capture.decode_id;capture.norm_count=capture.output_count=0;capture.hidden.clear();auto before=Clock::now();int rc=llama_decode(ctx.get(),b);llama_synchronize(ctx.get());
                report["decode_calls"].push_back({{"decode_id",capture.decode_id},{"offset",offset},{"input_tokens",b.n_tokens},{"return_code",rc},{"result_norm_count",capture.norm_count},{"result_output_count",capture.output_count},{"elapsed_s",std::chrono::duration<double>(Clock::now()-before).count()}});
                if(rc!=0||abort_compute(&capture))throw std::runtime_error(capture.error.empty()?"Actual decode failed/aborted/deadline":capture.error);
            }
            if(mode=="embedding-counter"){
                if(capture.norm_count!=1||capture.output_count!=0||capture.hidden.empty())throw std::runtime_error("Embedding counterproof did not show native norm without output projection");
                auto * h=llama_get_embeddings_ith(ctx.get(),-1);if(!h)throw std::runtime_error("Actual separate embedding getter unavailable");
                report["embedding_last_state"]=std::vector<float>(h,h+capture.dimension);report["callback_last_state"]=capture.hidden;
                report["logits_computed"]=false;report["logits"]=nullptr;report["counterproof"]="LFM2 result_norm observed, result_output absent; allocated logits buffer is not computed-logit evidence";
            } else {
                if(mode=="live"&&(capture.norm_count!=1||capture.output_count!=1||capture.hidden.empty()))throw std::runtime_error("No unique same-decode hidden/logit capture");
                if(mode=="live")report["live_last_state"]=capture.hidden;
                report["first_position"]=logits_result(ctx.get(),vocabulary);report["logits_computed"]=true;
                report["continuation"]=json::array();int next=report["first_position"]["greedy_token_id"];
                for(int i=0;i<continuations;++i){b.n_tokens=1;b.token[0]=next;b.pos[0]=tokens.size()+i;b.n_seq_id[0]=1;b.seq_id[0][0]=0;b.logits[0]=1;++capture.decode_id;capture.norm_count=capture.output_count=0;capture.hidden.clear();int rc=llama_decode(ctx.get(),b);llama_synchronize(ctx.get());if(rc||abort_compute(&capture))throw std::runtime_error("Actual continuation decode failed/aborted");if(mode=="live"&&(capture.norm_count!=1||capture.output_count!=1))throw std::runtime_error("Continuation capture mismatch");auto step=logits_result(ctx.get(),vocabulary);report["continuation"].push_back({{"input_token_id",next},{"position",b.pos[0]},{"greedy_next_token_id",step["greedy_token_id"]}});next=step["greedy_token_id"];}
            }
        } catch(...) {llama_batch_free(b);throw;}llama_batch_free(b);
        if(mode!="embedding-counter") {
            const auto * vocab=llama_model_get_vocab(model.get());
            std::vector<llama_token> output_tokens={report["first_position"]["greedy_token_id"].get<int>()};
            for(const auto & step:report["continuation"])output_tokens.push_back(step["greedy_next_token_id"].get<int>());
            std::string preview;
            for(auto token:output_tokens){
                std::vector<char> piece(128);int n=llama_token_to_piece(vocab,token,piece.data(),int(piece.size()),0,false);
                if(n<0){piece.resize(size_t(-n));n=llama_token_to_piece(vocab,token,piece.data(),int(piece.size()),0,false);}
                if(n<0||n>int(piece.size()))throw std::runtime_error("Actual token decoding failed");
                preview.append(piece.data(),size_t(n));
            }
            report["decoded_native_preview"]=preview;report["decoded_native_token_ids"]=output_tokens;
        }
        report["callback_records"]=capture.records;report["elapsed_s"]=std::chrono::duration<double>(Clock::now()-started).count();report["status"]="READONLY_NATIVE_PORT_OBSERVED";save_json(out,report);return 0;
    } catch(const std::exception & e) {
        report["status"]="READONLY_NATIVE_PORT_FAILED";report["error"]=e.what();if(!out.empty()){try{save_json(out,report);}catch(...) {}}
        std::cerr<<report.dump()<<'\n';return 1;
    }
}
