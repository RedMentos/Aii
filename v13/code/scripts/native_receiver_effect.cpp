// Isolated bounded receiver-effect diagnostic; no B3/production authority.
#define main v13_readonly_observer_main
#include "native_prefill_worker.cpp"
#undef main
#include <cstdlib>

static std::string hash_bytes(const void * data,size_t n){sha256_t s;sha256_init(&s);sha256_update(&s,static_cast<const unsigned char*>(data),n);unsigned char h[32];sha256_final(&s,h);std::ostringstream out;for(auto c:h)out<<std::hex<<std::setw(2)<<std::setfill('0')<<int(c);return out.str();}
static json unique_payload(const std::string & text){
    if(text.size()>65536)throw std::runtime_error("Receiver payload exceeds64KiB");
    std::vector<std::set<std::string>> stack;
    auto callback=[&](int,json::parse_event_t event,json & value){if(event==json::parse_event_t::object_start)stack.emplace_back();if(event==json::parse_event_t::key&&!stack.back().insert(value.get<std::string>()).second)throw std::runtime_error("Duplicate receiver payload key");if(event==json::parse_event_t::object_end)stack.pop_back();return true;};
    return json::parse(text,callback);
}
static std::vector<float> bounded_delta(const json & input,const json & expected){
    const std::set<std::string> fields={"schema","scope","source_id","nonce","model_sha256","runner_library_sha256","backend_manifest_sha256","context_source_sha256","token_file_sha256","target_tensor","target_tensor_before_sha256","dimension","delta_vector"};
    if(!input.is_object()||input.size()!=fields.size())throw std::runtime_error("Exact typed receiver vector fields required");
    for(const auto & key:fields)if(!input.contains(key))throw std::runtime_error("Missing typed receiver vector field");
    for(auto key:{"schema","scope","source_id","nonce","model_sha256","runner_library_sha256","backend_manifest_sha256","context_source_sha256","token_file_sha256","target_tensor","target_tensor_before_sha256"})if(!input[key].is_string())throw std::runtime_error("Exact string receiver binding required");
    if(input["schema"]!="V13_AUTHORED_RECEIVER_EFFECT_VECTOR_V1"||input["scope"]!="AUTHORED_NUMERIC_DIAGNOSTIC"||input["target_tensor"]!="result_norm"||input["source_id"].get<std::string>().empty()||input["source_id"].get<std::string>().size()>128)throw std::runtime_error("Receiver diagnostic source/scope/tensor mismatch");
    for(auto key:{"nonce","model_sha256","runner_library_sha256","backend_manifest_sha256","context_source_sha256","token_file_sha256"})if(input[key]!=expected.at(key))throw std::runtime_error("Stale/mismatched receiver binding");
    if(!input["dimension"].is_number_integer()||input["dimension"].is_boolean()||input["dimension"]!=1024||!input["delta_vector"].is_array()||input["delta_vector"].size()!=1024)throw std::runtime_error("Exact1024 receiver dimension required");
    const auto digest=input["target_tensor_before_sha256"].get<std::string>();if(digest.size()!=64||!std::all_of(digest.begin(),digest.end(),[](unsigned char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');}))throw std::runtime_error("Exact native tensor SHA required");
    std::vector<float> delta;double norm=0;
    for(const auto & value:input["delta_vector"]){if(!value.is_number()||value.is_boolean())throw std::runtime_error("Finite numeric receiver vector required");double d=value.get<double>();if(!std::isfinite(d))throw std::runtime_error("Nonfinite receiver vector");float f=float(d);if(!std::isfinite(f))throw std::runtime_error("Receiver F32 overflow");norm+=double(f)*f;delta.push_back(f);}
    if(std::sqrt(norm)>.125)throw std::runtime_error("Receiver L2 update exceeds0.125 BOOT cap");
    return delta;
}
struct Receiver {Capture capture;ggml_tensor * norm=nullptr;int frame=0;bool armed=false,diagnostic=false,applied=false,graph_verified=false;std::vector<float> delta,before,after;std::string expected_tensor_hash,before_hash,after_hash;int writes=0;json hook_events=json::array();double update_norm=0,relative_update=0;};
static bool receiver_abort(void * opaque){auto & r=*static_cast<Receiver*>(opaque);return abort_compute(&r.capture);}
static bool receiver_callback(ggml_tensor * tensor,bool ask,void * opaque) noexcept {
    auto & r=*static_cast<Receiver*>(opaque);auto & c=r.capture;
    const bool norm=std::strcmp(ggml_get_name(tensor),"result_norm")==0,output=std::strcmp(ggml_get_name(tensor),"result_output")==0;
    if(!c.active||!r.armed||(!norm&&!output)||tensor->ne[1]<=0)return false;
    try {
        if(ask){
            if(norm)return true;
            // Scheduler has completed/synchronized result_norm; this current
            // output node has not yet been submitted for computation.
            if(!r.norm||r.frame!=c.decode_id||c.norm_count!=1||tensor->op!=GGML_OP_MUL_MAT||tensor->src[1]!=r.norm)throw std::runtime_error("Unverified/stale receiver projection dataflow; capability blocked");
            r.graph_verified=true;
            if(r.diagnostic){
                if(r.applied||receiver_abort(&r))throw std::runtime_error("Cancelled/expired/duplicate receiver write refused");
                if(r.before_hash!=r.expected_tensor_hash)throw std::runtime_error("Native receiver tensor SHA mismatch before write");
                if(r.norm->flags&GGML_TENSOR_FLAG_PARAM)throw std::runtime_error("Receiver points to model parameter");
                auto buffer=r.norm->view_src?r.norm->view_src->buffer:r.norm->buffer;
                if(!buffer||!ggml_backend_buffer_is_host(buffer)||ggml_backend_buffer_get_usage(buffer)!=GGML_BACKEND_BUFFER_USAGE_COMPUTE)throw std::runtime_error("Receiver requires actual host CPU buffer");
                r.after=r.before;double change=0,base=0;
                for(size_t i=0;i<r.after.size();++i){if(r.delta[i]!=0)r.after[i]+=r.delta[i];if(!std::isfinite(r.after[i]))throw std::runtime_error("Nonfinite receiver state after perturbation");double d=double(r.after[i])-r.before[i];change+=d*d;base+=double(r.before[i])*r.before[i];}
                r.update_norm=std::sqrt(change);r.relative_update=base>1e-20?std::sqrt(change/base):INFINITY;
                if(r.update_norm>.125||r.relative_update>.01)throw std::runtime_error("Actual F32 receiver norm/relative cap exceeded before write");
                if(receiver_abort(&r))throw std::runtime_error("Receiver cancelled before write");
                if(r.update_norm>0){ggml_backend_tensor_set(r.norm,r.after.data(),0,1024*sizeof(float));++r.writes;std::vector<float> readback(1024);ggml_backend_tensor_get(r.norm,readback.data(),0,1024*sizeof(float));if(std::memcmp(readback.data(),r.after.data(),1024*sizeof(float)))throw std::runtime_error("Actual receiver write/readback mismatch");}
                r.after_hash=hash_bytes(r.after.data(),1024*sizeof(float));r.applied=true;
            }
            r.hook_events.push_back({{"phase","OUTPUT_ASK_BEFORE_MATMUL"},{"decode_id",c.decode_id},{"writes",r.writes},{"source_relation","result_output.src[1]==same_frame_result_norm"}});
            return true;
        }
        if(norm){
            if(tensor->type!=GGML_TYPE_F32||tensor->ne[0]!=1024||tensor->ne[1]!=1||tensor->ne[2]!=1||tensor->ne[3]!=1||!ggml_is_contiguous(tensor))throw std::runtime_error("Receiver selected-row shape/type/stride unsupported");
            if(!observe(tensor,false,&c))throw std::runtime_error(c.error);
            r.norm=tensor;r.frame=c.decode_id;r.before=c.hidden;r.before_hash=hash_bytes(r.before.data(),1024*sizeof(float));r.hook_events.push_back({{"phase","NORM_COMPLETED_AND_SYNCHRONIZED"},{"decode_id",c.decode_id},{"norm_sha256",r.before_hash}});return true;
        }
        if(!r.graph_verified||tensor->op!=GGML_OP_MUL_MAT||tensor->src[1]!=r.norm||(r.diagnostic&&!r.applied))throw std::runtime_error("Receiver projection computed without verified same-frame hook");
        r.hook_events.push_back({{"phase","OUTPUT_MATMUL_COMPLETED"},{"decode_id",c.decode_id}});return observe(tensor,false,&c);
    }catch(const std::exception & e){c.error=e.what();return ask?true:false;}
}
static json receiver_guards(){
    json expected={{"nonce","receiver-0123456789"},{"model_sha256","m"},{"runner_library_sha256","r"},{"backend_manifest_sha256","b"},{"context_source_sha256","c"},{"token_file_sha256","t"}};
    json good=expected;good.update({{"schema","V13_AUTHORED_RECEIVER_EFFECT_VECTOR_V1"},{"scope","AUTHORED_NUMERIC_DIAGNOSTIC"},{"source_id","authored-fixture"},{"target_tensor","result_norm"},{"target_tensor_before_sha256",std::string(64,'a')},{"dimension",1024},{"delta_vector",std::vector<float>(1024,0)}});
    json checks={{"zero_vector_valid",bounded_delta(good,expected).size()==1024}};auto reject=[&](const std::string & key,const json & x){try{bounded_delta(x,expected);checks[key]=false;}catch(const std::exception &){checks[key]=true;}};
    for(auto key:{"nonce","model_sha256","runner_library_sha256","backend_manifest_sha256","context_source_sha256","token_file_sha256","target_tensor","scope"}){auto x=good;x[key]="wrong";reject(std::string("mismatch_")+key,x);}
    auto x=good;x["delta_vector"]=std::vector<float>(1023,0);reject("wrong_shape",x);x=good;x["dimension"]=true;reject("bool_dimension",x);x=good;x["delta_vector"][0]=true;reject("bool_coordinate",x);x=good;x["delta_vector"][0]=std::numeric_limits<double>::infinity();reject("nonfinite_coordinate",x);x=good;x["delta_vector"][0]=.126;reject("oversize_norm",x);x=good;x["target_tensor_before_sha256"]="stale";reject("bad_tensor_hash",x);x=good;x["extra"]=1;reject("extra_field",x);
    x=good;x["delta_vector"]=std::vector<float>(1024,.003f);checks["bounded_nonzero_valid"]=bounded_delta(x,expected).size()==1024;
    Receiver r;r.capture.deadline=Clock::now()-std::chrono::seconds(1);checks["expired_abort"]=receiver_abort(&r);r.capture.deadline=Clock::now()+std::chrono::seconds(1);r.capture.error="stale";checks["error_abort"]=receiver_abort(&r);
    r.capture.error.clear();interrupted=1;checks["cancel_abort"]=receiver_abort(&r);interrupted=0;
    ggml_tensor output_node{};std::strcpy(output_node.name,"result_output");output_node.ne[1]=1;output_node.op=GGML_OP_MUL_MAT;
    Receiver stale;stale.capture.active=true;stale.capture.deadline=Clock::now()+std::chrono::seconds(1);stale.armed=true;
    receiver_callback(&output_node,true,&stale);checks["stale_graph_refused_before_write"]=stale.writes==0&&!stale.capture.error.empty();
    ggml_tensor norm_node{};Receiver duplicate;duplicate.capture.active=true;duplicate.capture.deadline=Clock::now()+std::chrono::seconds(1);duplicate.capture.norm_count=1;duplicate.armed=true;duplicate.diagnostic=true;duplicate.applied=true;duplicate.norm=&norm_node;output_node.src[1]=&norm_node;
    receiver_callback(&output_node,true,&duplicate);checks["duplicate_write_refused_before_write"]=duplicate.writes==0&&!duplicate.capture.error.empty();
    try{unique_payload("{\"delta\":1,\"delta\":2}");checks["duplicate_payload_keys_refused"]=false;}catch(const std::exception &){checks["duplicate_payload_keys_refused"]=true;}
    try{unique_payload(std::string(65537,' '));checks["oversize_payload_refused"]=false;}catch(const std::exception &){checks["oversize_payload_refused"]=true;}
    bool pass=std::all_of(checks.begin(),checks.end(),[](const json & x){return x==true;});return {{"schema","V13_RECEIVER_TYPED_GUARDS_V1"},{"status",pass?"GUARD_PASS":"GUARD_FAIL"},{"checks",checks},{"native_inference_performed",false}};
}
int main(int argc,char ** argv){
    if(argc==2&&std::string(argv[1])=="--guard-test"){auto g=receiver_guards();std::cout<<g.dump()<<std::endl;return g["status"]=="GUARD_PASS"?0:1;}
    json report={{"schema","V13_BOUNDED_RECEIVER_EFFECT_DIAGNOSTIC_V1"},{"production_authority",0},{"receiver_authority",0},{"training_authority",0},{"scope","AUTHORED_NUMERIC_DIAGNOSTIC"},{"pid",getpid()}};std::string output;
    try{
        std::map<std::string,std::string> a;for(int i=1;i<argc;i+=2){if(i+1>=argc||std::string(argv[i]).rfind("--",0)!=0||a.count(argv[i]))throw std::runtime_error("Unique --key value required");a[argv[i]]=argv[i+1];}
        const std::set<std::string> keys={"--model","--tokens","--output","--model-sha256","--lib-sha256","--backend-pins","--context-source-sha256","--nonce","--mode","--delta","--delta-sha256"};for(const auto & item:a)if(!keys.count(item.first))throw std::runtime_error("Unknown receiver argument");
        for(auto key:{"--model","--tokens","--output","--model-sha256","--lib-sha256","--backend-pins","--context-source-sha256","--nonce","--mode"})if(!a.count(key))throw std::runtime_error(std::string("Missing ")+key);
        output=a.at("--output");if(a.at("--nonce").size()<16||a.at("--nonce").size()>64||a.at("--context-source-sha256").size()!=64||!std::all_of(a.at("--context-source-sha256").begin(),a.at("--context-source-sha256").end(),[](unsigned char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');}))throw std::runtime_error("Receiver nonce/context SHA bound");auto mode=a.at("--mode");if(mode!="baseline"&&mode!="zero"&&mode!="nonzero")throw std::runtime_error("Receiver mode baseline/zero/nonzero required");
        report["mode"]=mode;report["model"]={{"path",a.at("--model")},{"sha256",sha_file(a.at("--model"))}};report["loaded_llama_library"]=library_identity(reinterpret_cast<const void*>(&llama_decode));report["loaded_ggml_library"]=library_identity(reinterpret_cast<const void*>(&ggml_backend_load_all));report["loaded_ggml_base_library"]=library_identity(reinterpret_cast<const void*>(&ggml_backend_tensor_set));
        if(report["model"]["sha256"]!=a.at("--model-sha256")||report["loaded_llama_library"]["sha256"]!=a.at("--lib-sha256"))throw std::runtime_error("Receiver model/runner SHA mismatch");
        std::ifstream tf(a.at("--tokens"));json input;tf>>input;if(!tf||!input.contains("token_ids")||!input["token_ids"].is_array()||input["token_ids"].empty()||input["token_ids"].size()>512||input.value("context_source_sha256","")!=a.at("--context-source-sha256"))throw std::runtime_error("Receiver exact token/context binding mismatch");
        std::vector<llama_token> tokens;for(const auto & value:input["token_ids"]){if(!value.is_number_integer()||value.is_boolean())throw std::runtime_error("Integer receiver token required");auto id=value.get<int64_t>();if(id<0||id>=65536)throw std::runtime_error("Receiver token outside vocabulary");tokens.push_back(int(id));}report["token_ids"]=tokens;report["token_file_sha256"]=sha_file(a.at("--tokens"));report["context_source_sha256"]=a.at("--context-source-sha256");
        std::string directory=report["loaded_ggml_library"]["path"];directory=directory.substr(0,directory.find_last_of('/'));ggml_backend_load_all_from_path(directory.c_str());std::ifstream pf(a.at("--backend-pins"));json pins;pf>>pins;if(!pf||!pins.contains("libraries"))throw std::runtime_error("Receiver backend pin missing");
        auto verify=[&](const json & id){char path[4096];auto name=id.at("path").get<std::string>();if(!realpath(name.c_str(),path)||!pins["libraries"].contains(path)||pins["libraries"].at(path)!=id.at("sha256"))throw std::runtime_error("Receiver loaded backend/library mismatch");};for(auto key:{"loaded_llama_library","loaded_ggml_library","loaded_ggml_base_library"})verify(report[key]);
        std::ifstream maps("/proc/self/maps");std::string line;std::set<std::string> cpu;while(std::getline(maps,line)){auto p=line.find('/');if(p!=std::string::npos&&line.substr(p).find("/libggml-cpu")!=std::string::npos)cpu.insert(line.substr(p));}if(cpu.empty()||!ggml_backend_reg_count())throw std::runtime_error("Receiver CPU backend unavailable");report["loaded_cpu_backends"]=json::array();for(const auto & p:cpu){json id={{"path",p},{"sha256",sha_file(p)}};verify(id);report["loaded_cpu_backends"].push_back(id);}report["all_loaded_libraries_verified"]=true;
        Receiver r;r.capture.dimension=1024;r.capture.deadline=Clock::now()+std::chrono::seconds(90);r.diagnostic=mode!="baseline";
        if(r.diagnostic){if(!a.count("--delta")||!a.count("--delta-sha256")||sha_file(a.at("--delta"))!=a.at("--delta-sha256"))throw std::runtime_error("Authored delta source SHA mismatch");std::ifstream df(a.at("--delta"));std::string text((std::istreambuf_iterator<char>(df)),{});json delta=unique_payload(text);if(!df)throw std::runtime_error("Malformed typed delta");json expected={{"nonce",a.at("--nonce")},{"model_sha256",a.at("--model-sha256")},{"runner_library_sha256",a.at("--lib-sha256")},{"backend_manifest_sha256",sha_file(a.at("--backend-pins"))},{"context_source_sha256",a.at("--context-source-sha256")},{"token_file_sha256",report["token_file_sha256"]}};r.delta=bounded_delta(delta,expected);r.expected_tensor_hash=delta["target_tensor_before_sha256"];report["typed_delta_source"]=delta;report["delta_source_sha256"]=a.at("--delta-sha256");bool allzero=std::all_of(r.delta.begin(),r.delta.end(),[](float x){return x==0;});if((mode=="zero")!=allzero)throw std::runtime_error("Receiver mode/vector zero mismatch");}
        std::signal(SIGINT,signal_handler);std::signal(SIGTERM,signal_handler);llama_backend_init();auto mp=llama_model_default_params();mp.n_gpu_layers=0;std::unique_ptr<llama_model,decltype(&llama_model_free)> model(llama_model_load_from_file(a.at("--model").c_str(),mp),llama_model_free);if(!model||llama_model_n_embd_out(model.get())!=1024||llama_vocab_n_tokens(llama_model_get_vocab(model.get()))!=65536)throw std::runtime_error("Receiver pinned C3 unavailable");
        auto cp=llama_context_default_params();cp.n_ctx=2048;cp.n_batch=128;cp.n_ubatch=128;cp.n_seq_max=1;cp.n_threads=2;cp.n_threads_batch=2;cp.embeddings=false;cp.pooling_type=LLAMA_POOLING_TYPE_NONE;cp.attention_type=LLAMA_ATTENTION_TYPE_UNSPECIFIED;cp.offload_kqv=false;cp.op_offload=false;cp.cb_eval=receiver_callback;cp.cb_eval_user_data=&r;cp.abort_callback=receiver_abort;cp.abort_callback_data=&r;
        std::unique_ptr<llama_context,decltype(&llama_free)> ctx(llama_init_from_model(model.get(),cp),llama_free);if(!ctx)throw std::runtime_error("Receiver actual context unavailable");auto batch=llama_batch_init(128,0,1);r.capture.active=true;
        try{for(size_t offset=0;offset<tokens.size();offset+=128){batch.n_tokens=std::min<size_t>(128,tokens.size()-offset);r.armed=offset+batch.n_tokens==tokens.size();for(int i=0;i<batch.n_tokens;++i){batch.token[i]=tokens[offset+i];batch.pos[i]=offset+i;batch.n_seq_id[i]=1;batch.seq_id[i][0]=0;batch.logits[i]=offset+i+1==tokens.size();}++r.capture.decode_id;r.capture.norm_count=r.capture.output_count=0;r.norm=nullptr;int rc=llama_decode(ctx.get(),batch);llama_synchronize(ctx.get());if(rc||receiver_abort(&r))throw std::runtime_error(r.capture.error.empty()?"Receiver actual decode aborted":r.capture.error);}
        if(!r.graph_verified||r.capture.norm_count!=1||r.capture.output_count!=1||(r.diagnostic&&!r.applied))throw std::runtime_error("Receiver effect graph not confirmed");
        report["first_position"]=logits_result(ctx.get(),65536);report["native_state_before"]=r.before;report["native_state_after"]=r.diagnostic?r.after:r.before;report["tensor_before_sha256"]=r.before_hash;report["tensor_after_sha256"]=r.diagnostic?r.after_hash:r.before_hash;report["ephemeral_tensor_writes"]=r.writes;report["actual_update_l2"]=r.update_norm;report["actual_relative_update"]=r.relative_update;report["verified_current_projection_consumes_norm"]=r.graph_verified;report["callback_records"]=r.capture.records;report["hook_events"]=r.hook_events;r.norm=nullptr;r.armed=false;
        }catch(...){llama_batch_free(batch);throw;}llama_batch_free(batch);report["model_sha256_after"]=sha_file(a.at("--model"));if(report["model_sha256_after"]!=a.at("--model-sha256"))throw std::runtime_error("Model weights changed");report["status"]="BOUNDED_RECEIVER_DIAGNOSTIC_COMPLETE";save_json(output,report);return 0;
    }catch(const std::exception & e){report["status"]="BOUNDED_RECEIVER_DIAGNOSTIC_FAILED";report["error"]=e.what();if(!output.empty()){try{save_json(output,report);}catch(...) {}}std::cerr<<report.dump()<<std::endl;return 1;}
}
