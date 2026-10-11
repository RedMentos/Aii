// Isolated native final-norm shadow experiment; zero production/commit authority.
// Build against exact llama.cpp b10964 public headers and release libraries.
// Separate FP32 master; frozen quantized trunk; one authored test-reference position.
// Local fixtures are not HUMAN_DECISION sources or approved training examples.
#include "llama.h"
#include "ggml.h"
#include "ggml-backend.h"
#include "nlohmann/json.hpp"
#include "native_norm_poll_policy.hpp"
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
#include <filesystem>
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
static std::string sha_bytes(const void * data,size_t length) {
    sha256_t state;sha256_init(&state);sha256_update(&state,static_cast<const unsigned char*>(data),length);
    unsigned char digest[32];sha256_final(&state,digest);std::ostringstream out;
    for(unsigned char value:digest)out<<std::hex<<std::setw(2)<<std::setfill('0')<<int(value);
    return out.str();
}
static std::string master_hash(const std::vector<float> & values) {
    return sha_bytes(values.data(),values.size()*sizeof(float));
}
static std::string tensor_hash(ggml_tensor * tensor) {
    sha256_t state;sha256_init(&state);std::vector<unsigned char> row_bytes(tensor->nb[1]);
    for(int64_t row_index=0;row_index<tensor->ne[1];++row_index){ggml_backend_tensor_get(tensor,row_bytes.data(),size_t(row_index)*tensor->nb[1],row_bytes.size());sha256_update(&state,row_bytes.data(),row_bytes.size());}
    unsigned char digest[32];sha256_final(&state,digest);std::ostringstream out;
    for(unsigned char value:digest)out<<std::hex<<std::setw(2)<<std::setfill('0')<<int(value);
    return out.str();
}
static json library_identity(const void * function) {
    Dl_info d{}; if (!dladdr(function,&d) || !d.dli_fname) throw std::runtime_error("Cannot resolve actual loaded library");
    return {{"path",d.dli_fname},{"sha256",sha_file(d.dli_fname)}};
}
static void save_json(const std::string & path,const json & data) {
    std::ofstream f(path,std::ios::binary|std::ios::trunc);if(!f)throw std::runtime_error("Cannot open output");f<<data.dump(2)<<'\n';f.flush();if(!f)throw std::runtime_error("Output write failed");
}
struct NormCapture {
    Clock::time_point deadline;
    bool active=false; int raw_count=0,norm_count=0,output_count=0;
    std::string error; std::vector<float> raw,scaled,original;
    int selected_batch_position=-1;json selection;
    ggml_tensor * observed_raw=nullptr;
    ggml_tensor * native_scale=nullptr; ggml_tensor * frozen_output=nullptr;
};
static bool stop(void * p) {
    auto & c=*static_cast<NormCapture*>(p);
    return interrupted || Clock::now()>=c.deadline || !c.error.empty();
}
static std::vector<float> row(ggml_tensor * t) {
    if(t->type!=GGML_TYPE_F32 || t->ne[0]!=1024 || t->ne[1]!=1 || t->ne[2]!=1 || t->ne[3]!=1 || t->nb[0]!=4)
        throw std::runtime_error("Selected final state is not one finite1024D native row");
    std::vector<float> v(1024);ggml_backend_tensor_get(t,v.data(),0,4096);
    double sum=0.;for(float x:v){if(!std::isfinite(x))throw std::runtime_error("Nonfinite state/master");sum+=double(x)*x;}
    if(sum<=1e-20)throw std::runtime_error("Zero native state/master");
    return v;
}
static bool norm_observer(ggml_tensor * t,bool ask,void * p) noexcept {
    auto & c=*static_cast<NormCapture*>(p);std::string name=ggml_get_name(t);
    bool wanted=name=="norm"||name=="result_norm"||name=="result_output";
    if(ask)return c.active && wanted;
    try {
        if(!c.active||!wanted)throw std::runtime_error("Unexpected observation");
        if(name=="norm") {
            if(t->op!=GGML_OP_RMS_NORM||++c.raw_count!=1)throw std::runtime_error("Ambiguous final RMSNorm");
            auto * residual=t->src[0];
            auto * selected=residual&&residual->op==GGML_OP_ADD?residual->src[0]:nullptr;
            if(!selected||selected->op!=GGML_OP_ADD||!selected->src[0]||!selected->src[1]||selected->src[0]->op!=GGML_OP_GET_ROWS||selected->src[1]->op!=GGML_OP_GET_ROWS||selected->src[0]->src[1]!=selected->src[1]->src[1])
                throw std::runtime_error("Pinned LFM2 last-layer residual output-row gather absent");
            auto * indices=selected->src[0]->src[1];int32_t selected_index=-1;
            if(!indices||indices->type!=GGML_TYPE_I32||ggml_nelements(indices)!=1)throw std::runtime_error("Unique actual last-output gather index absent");
            ggml_backend_tensor_get(indices,&selected_index,0,sizeof(selected_index));
            if(selected_index!=c.selected_batch_position)throw std::runtime_error("Actual final RMSNorm output gather selected wrong input token");
            c.selection["actual_output_gather_index"]=selected_index;
            c.selection["selected_rms_norm_shape"]={t->ne[0],t->ne[1],t->ne[2],t->ne[3]};
            c.selection["selected_rms_norm_strides_bytes"]={t->nb[0],t->nb[1],t->nb[2],t->nb[3]};
            c.observed_raw=t;
            c.raw=row(t);
        } else if(name=="result_norm") {
            if(++c.norm_count!=1||c.raw_count!=1||t->op!=GGML_OP_MUL||t->src[0]!=c.observed_raw||!t->src[1]||std::strcmp(ggml_get_name(t->src[1]),"token_embd_norm.weight"))
                throw std::runtime_error("Exact native final scale handle absent");
            c.native_scale=t->src[1];c.original=row(c.native_scale);c.scaled=row(t);
            for(size_t i=0;i<1024;++i)if(c.scaled[i]!=float(c.raw[i]*c.original[i]))throw std::runtime_error("Actual result_norm differs from selected raw norm times exact native scale");
            c.selection["all_1024_scale_products_exact"]=true;
        } else {
            if(++c.output_count!=1||c.norm_count!=1||t->op!=GGML_OP_MUL_MAT||!t->src[0]||!t->src[1]||std::strcmp(ggml_get_name(t->src[1]),"result_norm"))
                throw std::runtime_error("Native final output matrix handle absent");
            auto * w=t->src[0];
            if(std::strcmp(ggml_get_name(w),"token_embd.weight")||w->op!=GGML_OP_NONE||w->type!=GGML_TYPE_Q6_K||w->ne[0]!=1024||w->ne[1]!=65536||w->ne[2]!=1||w->ne[3]!=1||!ggml_backend_buffer_is_host(w->buffer))
                throw std::runtime_error("Exact frozen CPU tied Q6_K output required");
            c.frozen_output=w;
        }
        return true;
    } catch(const std::exception & e){c.error=e.what();return false;}
}
struct Tail {
    ggml_backend_t cpu=nullptr;ggml_backend_sched_t sched=nullptr;
    ggml_context * stat=nullptr,*compute=nullptr;ggml_backend_buffer_t buffer=nullptr;
    ggml_tensor * input=nullptr,*master=nullptr,*labels=nullptr,*logits=nullptr,*loss=nullptr,*gradient=nullptr;
    ggml_cgraph * graph=nullptr;NormCapture & guard;
    explicit Tail(NormCapture & c):guard(c) {
        try {
            cpu=ggml_backend_init_by_type(GGML_BACKEND_DEVICE_TYPE_CPU,nullptr);if(!cpu)throw std::runtime_error("No actual CPU backend");
            auto * reg=ggml_backend_dev_backend_reg(ggml_backend_get_device(cpu));
            auto threads=reinterpret_cast<ggml_backend_set_n_threads_t>(ggml_backend_reg_get_proc_address(reg,"ggml_backend_set_n_threads"));
            auto abort=reinterpret_cast<ggml_backend_set_abort_callback_t>(ggml_backend_reg_get_proc_address(reg,"ggml_backend_set_abort_callback"));
            if(!threads||!abort)throw std::runtime_error("CPU bounded threads/abort unavailable");
            threads(cpu,2);abort(cpu,stop,&guard);
            sched=ggml_backend_sched_new(&cpu,nullptr,1,1024,false,false);if(!sched)throw std::runtime_error("Tail scheduler unavailable");
            stat=ggml_init({65536,nullptr,true});compute=ggml_init({1024*1024,nullptr,true});if(!stat||!compute)throw std::runtime_error("Tail metadata allocation failed");
            input=ggml_new_tensor_2d(stat,GGML_TYPE_F32,1024,1);ggml_set_name(input,"isolated_raw_norm");ggml_set_input(input);
            master=ggml_new_tensor_1d(stat,GGML_TYPE_F32,1024);ggml_set_name(master,"isolated_token_embd_norm_master");ggml_set_param(master);
            labels=ggml_new_tensor_2d(stat,GGML_TYPE_F32,65536,1);ggml_set_name(labels,"authored_fixture_first_response_label");ggml_set_input(labels);
            buffer=ggml_backend_alloc_ctx_tensors(stat,cpu);if(!buffer)throw std::runtime_error("Tail static buffers unavailable");
            auto * scaled=ggml_mul(compute,input,master);logits=ggml_mul_mat(compute,c.frozen_output,scaled);ggml_set_output(logits);
            loss=ggml_cross_entropy_loss(compute,logits,labels);ggml_set_loss(loss);ggml_set_output(loss);
            graph=ggml_new_graph_custom(compute,1024,true);ggml_build_forward_expand(graph,loss);
            ggml_build_backward_expand(compute,graph,nullptr);gradient=ggml_graph_get_grad(graph,master);
            if(!gradient||!ggml_are_same_shape(gradient,master))throw std::runtime_error("Native1024D master gradient absent");
            ggml_set_output(gradient);
            if(!ggml_backend_sched_alloc_graph(sched,graph))throw std::runtime_error("Tail graph allocation failed");
        } catch(...){cleanup();throw;}
    }
    void cleanup(){if(sched)ggml_backend_sched_free(sched);if(buffer)ggml_backend_buffer_free(buffer);if(compute)ggml_free(compute);if(stat)ggml_free(stat);if(cpu)ggml_backend_free(cpu);sched=nullptr;buffer=nullptr;compute=stat=nullptr;cpu=nullptr;}
    ~Tail(){cleanup();}
    json evaluate(const std::vector<float> & weights,int target) {
        if(stop(&guard))throw std::runtime_error("Cancelled/deadline before tail forward/backward");
        ggml_graph_reset(graph);ggml_backend_tensor_set(input,guard.raw.data(),0,4096);ggml_backend_tensor_set(master,weights.data(),0,4096);
        ggml_backend_tensor_memset(labels,0,0,65536*4);float one=1.;ggml_backend_tensor_set(labels,&one,size_t(target)*4,4);
        auto before=Clock::now();auto status=ggml_backend_sched_graph_compute(sched,graph);ggml_backend_sched_synchronize(sched);
        if(status!=GGML_STATUS_SUCCESS||stop(&guard))throw std::runtime_error("Actual native tail forward/backward failed or aborted");
        float l;std::vector<float> g(1024),z(65536);ggml_backend_tensor_get(loss,&l,0,4);ggml_backend_tensor_get(gradient,g.data(),0,4096);ggml_backend_tensor_get(logits,z.data(),0,z.size()*4);
        if(!std::isfinite(l))throw std::runtime_error("Nonfinite native loss");
        for(float x:g)if(!std::isfinite(x))throw std::runtime_error("Nonfinite native gradient");
        for(float x:z)if(!std::isfinite(x))throw std::runtime_error("Nonfinite native logits");
        return {{"loss",l},{"gradient",g},{"logits",z},{"compute_status",ggml_status_to_string(status)},{"elapsed_s",std::chrono::duration<double>(Clock::now()-before).count()},{"scheduler_buffer_bytes",ggml_backend_sched_get_buffer_size(sched,cpu)}};
    }
};
static json native_prefill(llama_context * ctx,const std::vector<llama_token> & ids,NormCapture & c) {
    llama_memory_clear(llama_get_memory(ctx),true);c.raw_count=c.norm_count=c.output_count=0;c.raw.clear();c.scaled.clear();c.active=false;c.observed_raw=nullptr;
    auto b=llama_batch_init(128,0,1);
    try {
        for(size_t offset=0;offset<ids.size();offset+=128){b.n_tokens=std::min<size_t>(128,ids.size()-offset);for(int i=0;i<b.n_tokens;++i){b.token[i]=ids[offset+i];b.pos[i]=offset+i;b.n_seq_id[i]=1;b.seq_id[i][0]=0;b.logits[i]=offset+i+1==ids.size();}
            c.active=offset+size_t(b.n_tokens)==ids.size();
            if(c.active){c.selected_batch_position=b.n_tokens-1;c.selection={{"decode_batch_offset",offset},{"decode_batch_token_count",b.n_tokens},{"requested_logits_local_positions",{b.n_tokens-1}},{"selection_contract","PINNED_LFM2_LAST_LAYER_SHARED_OUTPUT_IDS_GATHER"}};}
            int rc=llama_decode(ctx,b);llama_synchronize(ctx);if(rc||stop(&c))throw std::runtime_error(c.error.empty()?"Native prefill aborted/deadline":c.error);}
        if(c.raw_count!=1||c.norm_count!=1||c.output_count!=1||!c.native_scale||!c.frozen_output)throw std::runtime_error("Incomplete unique final native norm/output capture");
        c.active=false;auto * ptr=llama_get_logits_ith(ctx,-1);if(!ptr)throw std::runtime_error("Actual native logits absent");std::vector<float> z(ptr,ptr+65536);for(float x:z)if(!std::isfinite(x))throw std::runtime_error("Nonfinite native logits");llama_batch_free(b);
        return {{"logits",z},{"greedy_token_id",std::max_element(z.begin(),z.end())-z.begin()},{"raw_final_norm",c.raw},{"scaled_final_norm",c.scaled},{"exact_selected_output_row",c.selection}};
    }catch(...){llama_batch_free(b);throw;}
}
static std::pair<double,std::vector<double>> reference_softmax(const std::vector<double> & z,int target) {
    double maximum=*std::max_element(z.begin(),z.end()),sum=0.;
    std::vector<double> p(z.size());
    for(size_t i=0;i<z.size();++i){if(!std::isfinite(z[i]))throw std::runtime_error("Nonfinite reference logit");p[i]=std::exp(z[i]-maximum);sum+=p[i];}
    if(!std::isfinite(sum)||sum<=0.)throw std::runtime_error("Invalid reference softmax");
    for(auto & value:p)value/=sum;
    return {maximum+std::log(sum)-z.at(target),p};
}
// Independent calculus: dequantize each immutable Q6_K row to FP32, then
// accumulate dot products and full-vocabulary softmax/gradients in FP64.
// The reference never uses GGML backward or the deployment Q8_K input quantizer.
static json reference_gradient(NormCapture & c,const std::vector<float> & weights,
                               int target,const json & native) {
    auto * tensor=c.frozen_output;
    auto * traits=ggml_get_type_traits(tensor->type);
    if(!traits||!traits->to_float||tensor->nb[1]!=ggml_row_size(tensor->type,1024))
        throw std::runtime_error("Exact contiguous Q6_K row dequantization unavailable");
    std::vector<unsigned char> encoded(tensor->nb[1]);std::vector<float> decoded(1024);
    std::vector<double> logits(65536),gradient(1024,0.),native_probability_gradient(1024,0.);
    std::vector<std::vector<float>> columns(32,std::vector<float>(65536));
    auto read_row=[&](int index){
        if(stop(&c))throw std::runtime_error("Cancelled/deadline during independent gradient reference");
        ggml_backend_tensor_get(tensor,encoded.data(),size_t(index)*tensor->nb[1],encoded.size());
        traits->to_float(encoded.data(),decoded.data(),1024);
        for(float x:decoded)if(!std::isfinite(x))throw std::runtime_error("Nonfinite actual dequantized output weight");
    };
    auto started=Clock::now();
    for(int v=0;v<65536;++v){
        read_row(v);double z=0.;
        for(int i=0;i<1024;++i)z+=double(decoded[i])*double(c.raw[i])*double(weights[i]);
        logits[v]=z;for(int k=0;k<32;++k)columns[k][v]=decoded[k*33];
    }
    auto math=reference_softmax(logits,target);
    auto actual_float=native.at("logits").get<std::vector<float>>();
    std::vector<double> actual(actual_float.begin(),actual_float.end());
    auto deployed=reference_softmax(actual,target);
    for(int v=0;v<65536;++v){
        read_row(v);double error=math.second[v]-(v==target?1.:0.),native_error=deployed.second[v]-(v==target?1.:0.);
        for(int i=0;i<1024;++i){double derivative=double(c.raw[i])*double(decoded[i]);gradient[i]+=error*derivative;native_probability_gradient[i]+=native_error*derivative;}
    }
    auto surrogate=native.at("gradient").get<std::vector<float>>();
    double surrogate_max=0.,mathematical_max=0.,forward_max=0.;bool surrogate_consistent=true;
    for(int i=0;i<1024;++i){double error=std::abs(double(surrogate[i])-native_probability_gradient[i]);surrogate_max=std::max(surrogate_max,error);mathematical_max=std::max(mathematical_max,std::abs(double(surrogate[i])-gradient[i]));if(error>1e-5+1e-3*std::abs(native_probability_gradient[i]))surrogate_consistent=false;}
    for(int v=0;v<65536;++v)forward_max=std::max(forward_max,std::abs(actual[v]-logits[v]));
    json finite=json::array();bool finite_consistent=true;
    // Fixed before inference: coordinates 0,33,...,1023, epsilon .001/.01.
    for(int k=0;k<32;++k){int coordinate=k*33;for(double eps:{.001,.01}){
        auto plus=logits,minus=logits;
        for(int v=0;v<65536;++v){double shift=eps*double(c.raw[coordinate])*double(columns[k][v]);plus[v]+=shift;minus[v]-=shift;}
        double numeric=(reference_softmax(plus,target).first-reference_softmax(minus,target).first)/(2*eps);
        double error=std::abs(numeric-gradient[coordinate]);bool pass=error<=1e-6+1e-4*std::abs(gradient[coordinate]);finite_consistent=finite_consistent&&pass;
        finite.push_back({{"coordinate",coordinate},{"epsilon",eps},{"analytic_fp64_gradient",gradient[coordinate]},{"numeric_fp64_gradient",numeric},{"absolute_error",error},{"pass",pass}});
    }}
    return {{"method","ACTUAL_Q6_K_ROWS_DEQUANTIZED_FP32_FP64_COMPLETE_VOCABULARY_REFERENCE"},
            {"full_vocabulary_size",65536},{"streamed_matrix_bytes_if_materialized",268435456},
            {"retained_coordinate_columns_bytes",32*65536*4},{"row_scratch_bytes",encoded.size()+4096},
            {"loss",math.first},{"logits",logits},{"gradient",gradient},
            {"gradient_under_native_quantized_forward_probabilities",native_probability_gradient},
            {"finite_differences",finite},{"reference_finite_difference_pass",finite_consistent},
            {"ggml_surrogate_vs_same_native_probabilities_pass",surrogate_consistent},
            {"ggml_surrogate_same_probability_max_absolute_error",surrogate_max},
            {"ggml_surrogate_vs_mathematical_gradient_max_absolute_error",mathematical_max},
            {"quantized_forward_vs_math_logits_max_absolute_error",forward_max},
            {"elapsed_s",std::chrono::duration<double>(Clock::now()-started).count()},
            {"exact_deployed_quantization_gradient_gate",false},
            {"tolerances_preregistered",{{"reference_atol",1e-6},{"reference_rtol",1e-4},{"surrogate_same_probability_atol",1e-5},{"surrogate_same_probability_rtol",1e-3}}}};
}
int main(int argc,char ** argv) {
    json report={{"schema","V13_ISOLATED_NATIVE_NORM_SHADOW_V2"},{"train_authority",0},{"receiver_authority",0},{"implemented_in_production",false},{"train_runner_proof",nullptr},{"source_bindings_independently_verified",false},{"pid",getpid()}};
    std::string output;
    try {
        std::map<std::string,std::string> a;for(int i=1;i<argc;i+=2){if(i+1>=argc||a.count(argv[i]))throw std::runtime_error("Unique --key value required");a[argv[i]]=argv[i+1];}
        for(auto key:{"--model","--example","--output","--model-sha256","--lib-sha256","--backend-pins"})if(!a.count(key))throw std::runtime_error(std::string("Missing ")+key);
        for(auto & kv:a)if(kv.first!="--model"&&kv.first!="--example"&&kv.first!="--output"&&kv.first!="--model-sha256"&&kv.first!="--lib-sha256"&&kv.first!="--candidate"&&kv.first!="--backend-pins"&&kv.first!="--forward-poll")throw std::runtime_error("Unknown argument");
        if(a.count("--forward-poll")&&a.at("--forward-poll")!="1")throw std::runtime_error("Forward poll must be explicitly1");
        output=a.at("--output");if(output==a.at("--model")||output==a.at("--example"))throw std::runtime_error("Output cannot replace input");
        std::ifstream f(a.at("--example"));json e;f>>e;
        if(!f||!e.is_object()||e.value("experiment_fixture_only",false)!=true||e.value("reference_origin",std::string())!="AUTHORED_EXPERIMENT_REFERENCE"||!e.contains("source_bindings")||!e["source_bindings"].is_object())
            throw std::runtime_error("Zero-authority authored experiment fixture and exact source bindings required");
        report["reference_origin"]="AUTHORED_EXPERIMENT_REFERENCE";
        report["human_training_approval_verified"]=false;
        report["source_authority"]=0;
        if(!e.contains("source_files")||!e["source_files"].is_object())throw std::runtime_error("Independently hashable source files required");
        for(auto key:{"context","reference","permission"}){
            auto s=e["source_bindings"].value(std::string(key)+"_sha256",std::string());
            auto path=e["source_files"].value(key,std::string());
            if(s.size()!=64||s.find_first_not_of("0123456789abcdef")!=std::string::npos||path.empty()||sha_file(path)!=s)
                throw std::runtime_error("Exact source-binding hash/file mismatch");
        }
        report["source_bindings_independently_verified"]=true;
        if(!e.contains("token_ids")||!e["token_ids"].is_array()||e["token_ids"].empty()||e["token_ids"].size()>512||!e.contains("target_token_id")||!e["target_token_id"].is_number_integer())throw std::runtime_error("Bounded exact token IDs and authored test-reference target required");
        std::vector<llama_token> ids;for(auto & t:e["token_ids"]){if(!t.is_number_integer()||t.is_boolean())throw std::runtime_error("Token ID integer required");int64_t x=t.get<int64_t>();if(x<0||x>=65536)throw std::runtime_error("Token outside pinned vocabulary");ids.push_back(llama_token(x));}
        int64_t target64=e["target_token_id"].get<int64_t>();if(target64<0||target64>=65536)throw std::runtime_error("Target outside vocabulary");int target=int(target64);
        report["source_bindings"]=e["source_bindings"];report["example_sha256"]=sha_file(a.at("--example"));report["token_ids"]=ids;report["reference_target_token_id"]=target;
        report["model_sha256"]=sha_file(a.at("--model"));report["loaded_library"]=library_identity(reinterpret_cast<const void*>(&llama_decode));
        if(report["model_sha256"]!=a.at("--model-sha256")||a.at("--model-sha256")!="e75f83268de11b2a1bcfab5f3b5c5c0c97569ddbbc0990aad88437e45b8ba292"||report["loaded_library"]["sha256"]!=a.at("--lib-sha256"))throw std::runtime_error("Actual pinned C3/library mismatch");
        std::signal(SIGINT,signal_handler);std::signal(SIGTERM,signal_handler);NormCapture c;c.deadline=Clock::now()+std::chrono::seconds(120);
        auto ggml_identity=library_identity(reinterpret_cast<const void*>(&ggml_backend_load_all_from_path));
        auto backend_directory=std::filesystem::path(ggml_identity.at("path").get<std::string>()).parent_path();
        ggml_backend_load_all_from_path(backend_directory.c_str());llama_backend_init();
        report["actual_loaded_ggml_loader_library"]=ggml_identity;
        report["actual_loaded_ggml_base_library"]=library_identity(reinterpret_cast<const void*>(&ggml_backend_tensor_get));
        std::ifstream pin_input(a.at("--backend-pins"));json pins;pin_input>>pins;
        if(!pin_input||!pins.is_object()||!pins.contains("libraries")||!pins["libraries"].is_object())throw std::runtime_error("Exact loaded backend library pins required");
        auto verify_library=[&](const json & identity){
            auto path=std::filesystem::canonical(identity.at("path").get<std::string>()).string();
            if(!pins["libraries"].contains(path)||pins["libraries"].at(path)!=identity.at("sha256"))throw std::runtime_error("Actual loaded library differs from installed build pins");
        };
        for(auto key:{"loaded_library","actual_loaded_ggml_loader_library","actual_loaded_ggml_base_library"})verify_library(report.at(key));
        std::ifstream maps("/proc/self/maps");std::string line;std::set<std::string> loaded;
        while(std::getline(maps,line)){auto slash=line.find('/');if(slash!=std::string::npos){auto path=line.substr(slash);if(path.find("/libggml-cpu")!=std::string::npos)loaded.insert(path);}}
        if(loaded.empty())throw std::runtime_error("No actual loaded CPU backend identified");
        report["actual_loaded_cpu_backend_libraries"]=json::array();
        for(const auto & path:loaded){json identity={{"path",path},{"sha256",sha_file(path)}};verify_library(identity);report["actual_loaded_cpu_backend_libraries"].push_back(identity);}
        report["all_loaded_libraries_verified"]=true;report["backend_pins_sha256"]=sha_file(a.at("--backend-pins"));
        auto mp=llama_model_default_params();mp.n_gpu_layers=0;mp.load_mode=LLAMA_LOAD_MODE_NONE;
        std::unique_ptr<llama_model,decltype(&llama_model_free)> model(llama_model_load_from_file(a.at("--model").c_str(),mp),llama_model_free);if(!model||llama_model_n_embd_out(model.get())!=1024||llama_vocab_n_tokens(llama_model_get_vocab(model.get()))!=65536)throw std::runtime_error("Pinned C3 model load/shape failed");
        auto cp=llama_context_default_params();cp.n_ctx=1024;cp.n_batch=128;cp.n_ubatch=128;cp.n_seq_max=1;cp.n_threads=cp.n_threads_batch=2;cp.embeddings=false;cp.offload_kqv=false;cp.op_offload=false;cp.abort_callback=stop;cp.abort_callback_data=&c;cp.cb_eval=norm_observer;cp.cb_eval_user_data=&c;
        std::unique_ptr<llama_context,decltype(&llama_free)> ctx(llama_init_from_model(model.get(),cp),llama_free);if(!ctx)throw std::runtime_error("Isolated context unavailable");
        auto before=native_prefill(ctx.get(),ids,c);auto original=c.original;
        auto native_scale=c.native_scale;auto frozen_output=c.frozen_output;
        report["native_before"]=before;report["original_master"]=original;
        report["original_master_sha256"]=master_hash(original);
        report["frozen_native_output_before_sha256"]=tensor_hash(frozen_output);
        std::vector<float> candidate=original;
        if(a.count("--candidate")){
            if(output==a.at("--candidate"))throw std::runtime_error("Output cannot replace candidate input");
            std::ifstream candidate_file(a.at("--candidate"));json checkpoint;candidate_file>>checkpoint;
            if(!candidate_file||checkpoint.value("schema",std::string())!="V13_ISOLATED_NATIVE_NORM_MASTER_V1"||checkpoint.value("tensor",std::string())!="token_embd_norm.weight"||checkpoint.value("precision",std::string())!="FP32"||checkpoint.value("model_sha256",std::string())!=report["model_sha256"]||checkpoint.value("original_master_sha256",std::string())!=report["original_master_sha256"]||checkpoint.at("source_bindings")!=e.at("source_bindings")||checkpoint.value("train_authority",-1)!=0)
                throw std::runtime_error("Candidate checkpoint source/model/master binding mismatch");
            candidate=checkpoint.at("values").get<std::vector<float>>();
            if(candidate.size()!=1024||master_hash(candidate)!=checkpoint.value("master_sha256",std::string()))throw std::runtime_error("Candidate master size/hash mismatch");
            double update=0.;for(size_t i=0;i<candidate.size();++i){if(!std::isfinite(candidate[i]))throw std::runtime_error("Nonfinite candidate master");double difference=double(candidate[i])-original[i];update+=difference*difference;}
            if(std::sqrt(update)>.0010001)throw std::runtime_error("Oversize candidate master update refused");
            ggml_backend_tensor_set(native_scale,candidate.data(),0,4096);report["native_candidate_reload"]=native_prefill(ctx.get(),ids,c);
            ggml_backend_tensor_set(native_scale,original.data(),0,4096);report["native_rollback"]=native_prefill(ctx.get(),ids,c);
            report["candidate_master_sha256"]=master_hash(candidate);report["candidate_file_sha256"]=sha_file(a.at("--candidate"));
            report["frozen_native_output_after_sha256"]=tensor_hash(frozen_output);
            report["original_gguf_unchanged"]=sha_file(a.at("--model"))==report["model_sha256"];
            if(report["frozen_native_output_after_sha256"]!=report["frozen_native_output_before_sha256"]||!report["original_gguf_unchanged"].get<bool>()||row(native_scale)!=original)throw std::runtime_error("Reload changed frozen output/base or failed master rollback");
            report["proof_gates_complete"]=false;report["status"]="ISOLATED_NATIVE_NORM_RELOAD_OBSERVATIONS_ONLY";
            auto partial=output+".partial";save_json(partial,report);if(std::rename(partial.c_str(),output.c_str()))throw std::runtime_error("Atomic reload report rename failed");return 0;
        }
        {
            Tail tail(c);auto base=tail.evaluate(original,target);report["native_tail_before"]=base;
            report["independent_gradient_reference"]=reference_gradient(c,original,target,base);
            auto grad=base["gradient"].get<std::vector<float>>();double norm=0.;for(float x:grad)norm+=double(x)*x;norm=std::sqrt(norm);double factor=std::min(.001,.001/std::max(norm,1e-20));
            for(size_t i=0;i<candidate.size();++i)candidate[i]=float(double(original[i])-factor*grad[i]);
            report["gradient_method"]="GGML_AUTODIFF_FIXED_DEQUANTIZED_OUTPUT_SURROGATE_NOT_EXACT_ACTIVATION_QUANTIZATION_DERIVATIVE";
            report["optimizer"]={{"type","SGD_NO_MOMENTUM"},{"learning_rate",.001},{"max_update_norm",.001},{"raw_gradient_norm",norm},{"effective_step_scale",factor}};
            auto baseline_z=base.at("logits").get<std::vector<float>>();
            double baseline_ce=reference_softmax(std::vector<double>(baseline_z.begin(),baseline_z.end()),target).first;
            double best_ce=baseline_ce;bool accepted=false;
            report["candidate_trials"]=json::array();report["candidate_acceptance_baseline_full_vocab_ce"]=baseline_ce;
            // Fixed preregistered factors, unchanged .001 norm cap. Every actual
            // quantized forward is retained; equality/worse/nonfinite cannot pass.
            auto observation_candidate=candidate;
            for(double scale:{1.,.5,.25,.125}){
                auto trial=original;double update_squared=0.;
                for(size_t i=0;i<trial.size();++i){trial[i]=float(double(original[i])-factor*scale*grad[i]);double difference=double(trial[i])-original[i];update_squared+=difference*difference;}
                auto measured=tail.evaluate(trial,target);auto z=measured.at("logits").get<std::vector<float>>();
                double actual_ce=reference_softmax(std::vector<double>(z.begin(),z.end()),target).first;
                bool improved=actual_ce<baseline_ce&&std::sqrt(update_squared)<=.0010001;
                report["candidate_trials"].push_back({{"step_factor",scale},{"update_l2",std::sqrt(update_squared)},{"actual_quantized_full_vocab_ce",actual_ce},{"strict_baseline_improvement",improved},{"master_sha256",master_hash(trial)},{"actual_quantized_tail",measured}});
                if(improved&&actual_ce<best_ce){accepted=true;candidate=trial;best_ce=actual_ce;}
            }
            if(!accepted)candidate=observation_candidate;
            report["candidate_acceptance"]={{"status",accepted?"EVALUATED_PASS_ISOLATED_ONLY":"EVALUATED_FAIL"},{"strict_improvement_required",true},{"accepted_for_training",false},{"accepted_observation_master",accepted},{"best_full_vocab_ce",best_ce},{"preregistered_step_factors",{1.,.5,.25,.125}},{"scope","ONE_AUTHORED_ROW_NO_RETENTION_APPROVAL_OR_PRODUCTION_AUTHORITY"}};
            if(a.count("--forward-poll")){
                // The original surrogate evidence above remains unchanged.
                report["surrogate_candidate_acceptance"]=report["candidate_acceptance"];
                report["surrogate_observation_master_sha256"]=master_hash(candidate);
                report["optimizer_kind"]="BOUNDED_ACTUAL_FORWARD_ONLY_POLL_NO_EXACT_DERIVATIVE";
                report["forward_poll_manifest"]={{"maximum_evaluations",v13_norm_poll::max_evaluations},{"directions",{"surrogate_unit_direction_not_exact_gradient","coordinate_0","coordinate_341","coordinate_682","coordinate_1023"}},{"radii",{.001,.0005}},{"signs",{-1,1}},{"max_update_norm",.0010001},{"full_vocabulary_ce_strict_improvement",true},{"adaptive_radius_or_direction",false},{"exact_quantized_gradient_gate",false}};
                auto trials=v13_norm_poll::candidates(original,grad);json observations=json::array();double poll_best=baseline_ce;bool found=false;std::vector<float> poll_candidate=original;json selected_tail;
                for(const auto & trial:trials){
                    json observation={{"direction",trial.direction},{"radius",trial.radius},{"sign",trial.sign},{"update_l2",trial.update_l2},{"master_sha256",master_hash(trial.values)},{"master_values",trial.values}};
                    if(trial.update_l2>v13_norm_poll::cap||trial.update_l2<=0.){observation["status"]="REFUSED_MASTER_NORM";observations.push_back(observation);continue;}
                    auto measured=tail.evaluate(trial.values,target);auto z=measured.at("logits").get<std::vector<float>>();double ce=reference_softmax(std::vector<double>(z.begin(),z.end()),target).first;
                    observation["actual_quantized_full_vocab_ce"]=ce;observation["actual_quantized_logits_fp32_sha256"]=master_hash(z);observation["compute_status"]=measured["compute_status"];observation["elapsed_s"]=measured["elapsed_s"];
                    bool improved=v13_norm_poll::improves(baseline_ce,ce,trial.update_l2);observation["strict_baseline_improvement"]=improved;observation["status"]=improved?"ISOLATED_FORWARD_IMPROVEMENT":"EVALUATED_FAIL";observations.push_back(observation);
                    if(improved&&ce<poll_best){poll_best=ce;poll_candidate=trial.values;selected_tail=measured;found=true;}
                }
                report["forward_poll_observations"]=observations;report["forward_poll_candidate_found"]=found;
                bool validated=false;double actual_candidate_ce=baseline_ce;
                if(found){
                    ggml_backend_tensor_set(native_scale,poll_candidate.data(),0,4096);auto actual=native_prefill(ctx.get(),ids,c);
                    auto full=actual.at("logits").get<std::vector<float>>(), predicted=selected_tail.at("logits").get<std::vector<float>>();double difference=0.;for(size_t i=0;i<full.size();++i)difference=std::max(difference,std::abs(double(full[i])-predicted[i]));
                    auto original_full=before.at("logits").get<std::vector<float>>();double original_full_ce=reference_softmax(std::vector<double>(original_full.begin(),original_full.end()),target).first;
                    double full_ce=reference_softmax(std::vector<double>(full.begin(),full.end()),target).first;actual_candidate_ce=full_ce;validated=difference<=1e-5&&full_ce<original_full_ce;
                    report["forward_poll_actual_native_validation"]={{"actual_native_prefill",actual},{"native_tail_logits_max_absolute_error",difference},{"actual_native_baseline_full_vocab_ce",original_full_ce},{"actual_native_full_vocab_ce",full_ce},{"strict_improvement",full_ce<original_full_ce},{"pass",validated}};
                    ggml_backend_tensor_set(native_scale,original.data(),0,4096);report["forward_poll_native_rollback"]=native_prefill(ctx.get(),ids,c);
                }
                if(validated){candidate=poll_candidate;report["candidate_acceptance"]={{"status","EVALUATED_PASS_ISOLATED_FORWARD_ONLY"},{"strict_improvement_required",true},{"accepted_for_training",false},{"accepted_observation_master",true},{"best_full_vocab_ce",actual_candidate_ce},{"scope","ONE_AUTHORED_ROW_FORWARD_ONLY_NO_RETENTION_APPROVAL_OR_PRODUCTION_AUTHORITY"}};}
                report["forward_poll_accepted_observation_master"]=validated;
                report["exact_quantized_gradient_gate"]=false;
            }
            report["native_tail_after"]=tail.evaluate(candidate,target);
            report["actual_quantized_forward_finite_differences"]=json::array();
            for(int k=0;k<4;++k){int coordinate=k*341;for(float eps:{.001f,.01f}){auto plus=original,minus=original;plus[coordinate]+=eps;minus[coordinate]-=eps;double upper=tail.evaluate(plus,target)["loss"],lower=tail.evaluate(minus,target)["loss"];report["actual_quantized_forward_finite_differences"].push_back({{"coordinate",coordinate},{"epsilon",eps},{"numeric_gradient",(upper-lower)/(2*eps)},{"ggml_surrogate_gradient",grad[coordinate]}});}}
        }
        if(native_scale!=c.native_scale||frozen_output!=c.frozen_output||row(native_scale)!=original)throw std::runtime_error("Native weight handle/master changed unexpectedly");
        ggml_backend_tensor_set(native_scale,candidate.data(),0,4096);report["native_after"]=native_prefill(ctx.get(),ids,c);
        ggml_backend_tensor_set(native_scale,original.data(),0,4096);report["native_rollback"]=native_prefill(ctx.get(),ids,c);
        report["candidate_master"]={{"tensor","token_embd_norm.weight"},{"shape",{1024}},{"precision","FP32"},{"values",candidate},{"trained_parameter_count",1024},{"stored_frozen_parameter_elements",229692160},{"master_weight_bytes",4096},{"optimizer_momentum_bytes",0},{"scope","ISOLATED_SHADOW_NO_IMPORT_AUTHORITY"}};
        report["candidate_master_sha256"]=master_hash(candidate);
        report["restored_original_master_sha256"]=master_hash(row(native_scale));
        report["frozen_native_output_after_sha256"]=tensor_hash(frozen_output);
        if(report["frozen_native_output_after_sha256"]!=report["frozen_native_output_before_sha256"]||row(native_scale)!=original)throw std::runtime_error("Frozen output modified or original master rollback failed");
        report["original_gguf_unchanged"]=sha_file(a.at("--model"))==report["model_sha256"];if(!report["original_gguf_unchanged"].get<bool>())throw std::runtime_error("Original GGUF changed");
        report["quantized_base_update_roundtrip"]="NOT_APPLICABLE_FINAL_SCALE_REMAINS_FP32_BASE_Q4_Q6_FROZEN";
        report["proof_gates_complete"]=false;report["status"]="ISOLATED_NATIVE_NORM_OBSERVATIONS_ONLY";
        json checkpoint={{"schema","V13_ISOLATED_NATIVE_NORM_MASTER_V1"},{"tensor","token_embd_norm.weight"},{"precision","FP32"},{"shape",{1024}},{"values",candidate},{"master_sha256",master_hash(candidate)},{"original_master_sha256",master_hash(original)},{"model_sha256",report["model_sha256"]},{"source_bindings",e.at("source_bindings")},{"train_authority",0},{"reference_origin","AUTHORED_EXPERIMENT_REFERENCE"},{"approval",false}};
        bool accepted=report.at("candidate_acceptance").at("accepted_observation_master").get<bool>();
        checkpoint["candidate_acceptance_status"]=report.at("candidate_acceptance").at("status");
        checkpoint["numerical_observation_only"]=!accepted;
        auto master_path=output+(accepted?".master.json":".observation-master.json"),master_partial=master_path+".partial";save_json(master_partial,checkpoint);if(std::rename(master_partial.c_str(),master_path.c_str()))throw std::runtime_error("Atomic isolated master rename failed");
        report["candidate_checkpoint"]={{"path",master_path},{"sha256",sha_file(master_path)}};
        auto partial=output+".partial";save_json(partial,report);if(std::rename(partial.c_str(),output.c_str()))throw std::runtime_error("Atomic report rename failed");return 0;
    } catch(const std::exception & e){report["status"]="ISOLATED_NATIVE_NORM_FAILED";report["error"]=e.what();if(!output.empty()){try{save_json(output+".failure.json",report);}catch(...) {}}std::cerr<<report.dump()<<'\n';return 1;}
}
