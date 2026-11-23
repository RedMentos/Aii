// Optional bounded l_out-6 -> norm-7 receiver diagnostic; no production authority.
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
    const std::set<std::string> fields={"schema","scope","source_id","nonce","model_sha256","runner_library_sha256","backend_manifest_sha256","context_source_sha256","token_file_sha256","target_tensor","target_tensor_before_sha256","dimension","delta_vector","architecture","layer_count","target_layer","next_consumer","sequence_id","target_token_position","decode_epoch"};
    if(!input.is_object()||input.size()!=fields.size())throw std::runtime_error("Exact typed receiver vector fields required");
    for(const auto & key:fields)if(!input.contains(key))throw std::runtime_error("Missing typed receiver vector field");
    for(auto key:{"schema","scope","source_id","nonce","model_sha256","runner_library_sha256","backend_manifest_sha256","context_source_sha256","token_file_sha256","target_tensor","target_tensor_before_sha256"})if(!input[key].is_string())throw std::runtime_error("Exact string receiver binding required");
    if(input["schema"]!="V13_AUTHORED_MIDLAYER_EFFECT_VECTOR_V1"||input["scope"]!="AUTHORED_NUMERIC_DIAGNOSTIC"||input["target_tensor"]!="l_out-6"||input["source_id"].get<std::string>().empty()||input["source_id"].get<std::string>().size()>128)throw std::runtime_error("Receiver diagnostic source/scope/tensor mismatch");
    for(auto key:{"nonce","model_sha256","runner_library_sha256","backend_manifest_sha256","context_source_sha256","token_file_sha256"})if(input[key]!=expected.at(key))throw std::runtime_error("Stale/mismatched receiver binding");
    if(!input["dimension"].is_number_integer()||input["dimension"].is_boolean()||input["dimension"]!=1024||!input["delta_vector"].is_array()||input["delta_vector"].size()!=1024)throw std::runtime_error("Exact1024 receiver dimension required");
    if(input["architecture"]!="lfm2"||input["next_consumer"]!="norm-7")throw std::runtime_error("Midlayer architecture/consumer mismatch");
    for(auto key:{"layer_count","target_layer","sequence_id","target_token_position","decode_epoch"})if(!input[key].is_number_integer()||input[key].is_boolean()||input[key]!=expected.at(key))throw std::runtime_error("Midlayer exact layer/position/epoch binding mismatch");
    const auto digest=input["target_tensor_before_sha256"].get<std::string>();if(digest.size()!=64||!std::all_of(digest.begin(),digest.end(),[](unsigned char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');}))throw std::runtime_error("Exact native tensor SHA required");
    std::vector<float> delta;double norm=0;
    for(const auto & value:input["delta_vector"]){if(!value.is_number()||value.is_boolean())throw std::runtime_error("Finite numeric receiver vector required");double d=value.get<double>();if(!std::isfinite(d))throw std::runtime_error("Nonfinite receiver vector");float f=float(d);if(!std::isfinite(f))throw std::runtime_error("Receiver F32 overflow");norm+=double(f)*f;delta.push_back(f);}
    if(std::sqrt(norm)>.125)throw std::runtime_error("Receiver L2 update exceeds0.125 BOOT cap");
    return delta;
}
struct Receiver {
    Capture capture;ggml_tensor * norm=nullptr;int frame=0,input_rows=0;size_t byte_offset=0;std::string phase="WAIT_SOURCE";
    bool armed=false,diagnostic=false,applied=false,graph_verified=false;std::vector<float> delta,before,after;
    std::string expected_tensor_hash,before_hash,after_hash,prefix_before,prefix_after;int writes=0;
    json hook_events=json::array();double update_norm=0,relative_update=0;
};
static bool receiver_abort(void * opaque){auto & r=*static_cast<Receiver*>(opaque);return abort_compute(&r.capture);}
static bool receiver_callback(ggml_tensor * tensor,bool ask,void * opaque) noexcept {
    auto & r=*static_cast<Receiver*>(opaque);auto & c=r.capture;
    if(!c.active||!r.armed||tensor->ne[1]<=0)return false;
    const bool source=std::strcmp(ggml_get_name(tensor),"l_out-6")==0;
    const bool consumer=std::strcmp(ggml_get_name(tensor),"norm-7")==0 && r.phase!="DONE";
    const bool final=std::strcmp(ggml_get_name(tensor),"result_norm")==0 || std::strcmp(ggml_get_name(tensor),"result_output")==0;
    if(final)return observe(tensor,ask,&c);
    if(!source&&!consumer)return false;
    try {
        if(ask){
            if(source){if(r.phase!="WAIT_SOURCE")throw std::runtime_error("Duplicate midlayer source frame");return true;}
            if(r.phase!="WAIT_CONSUMER"||!r.norm||r.frame!=c.decode_id||tensor->op!=GGML_OP_RMS_NORM||tensor->src[0]!=r.norm||tensor->ne[0]!=1024||tensor->ne[1]!=r.input_rows)throw std::runtime_error("Stale/unverified current next-layer RMS dataflow; capability blocked");
            r.graph_verified=true;
            if(r.diagnostic){
                if(r.applied||receiver_abort(&r))throw std::runtime_error("Cancelled/expired/duplicate midlayer write refused");
                if(r.before_hash!=r.expected_tensor_hash)throw std::runtime_error("Midlayer native tensor SHA mismatch before write");
                if(r.norm->flags&GGML_TENSOR_FLAG_PARAM)throw std::runtime_error("Midlayer receiver points to model parameter");
                auto buffer=r.norm->view_src?r.norm->view_src->buffer:r.norm->buffer;
                if(!buffer||!ggml_backend_buffer_is_host(buffer)||ggml_backend_buffer_get_usage(buffer)!=GGML_BACKEND_BUFFER_USAGE_COMPUTE)throw std::runtime_error("Midlayer requires actual host COMPUTE buffer");
                r.after=r.before;double change=0,base=0;
                for(size_t i=0;i<1024;++i){if(r.delta[i]!=0)r.after[i]+=r.delta[i];if(!std::isfinite(r.after[i]))throw std::runtime_error("Nonfinite midlayer state after perturbation");double d=double(r.after[i])-r.before[i];change+=d*d;base+=double(r.before[i])*r.before[i];}
                r.update_norm=std::sqrt(change);r.relative_update=base>1e-20?std::sqrt(change/base):INFINITY;
                if(r.update_norm>.125||r.relative_update>.01)throw std::runtime_error("Midlayer applied norm/relative cap exceeded before write");
                if(receiver_abort(&r))throw std::runtime_error("Midlayer cancelled before write");
                if(r.update_norm>0){ggml_backend_tensor_set(r.norm,r.after.data(),r.byte_offset,1024*sizeof(float));++r.writes;std::vector<float> back(1024);ggml_backend_tensor_get(r.norm,back.data(),r.byte_offset,1024*sizeof(float));if(std::memcmp(back.data(),r.after.data(),1024*sizeof(float)))throw std::runtime_error("Midlayer write/readback mismatch");}
                r.after_hash=hash_bytes(r.after.data(),1024*sizeof(float));r.applied=true;
            }
            std::vector<unsigned char> prefix(r.byte_offset);if(!prefix.empty())ggml_backend_tensor_get(r.norm,prefix.data(),0,prefix.size());r.prefix_after=hash_bytes(prefix.data(),prefix.size());if(r.prefix_after!=r.prefix_before)throw std::runtime_error("Midlayer write altered earlier token rows");
            r.phase="CONSUMER_ASKED";r.hook_events.push_back({{"phase","NEXT_LAYER_RMS_ASK_BEFORE_COMPUTE"},{"decode_id",c.decode_id},{"source","l_out-6"},{"consumer","norm-7"},{"writes",r.writes},{"selected_row",r.input_rows-1}});return true;
        }
        if(source){
            if(r.phase!="WAIT_SOURCE"||tensor->type!=GGML_TYPE_F32||tensor->ne[0]!=1024||tensor->ne[1]!=r.input_rows||tensor->ne[2]!=1||tensor->ne[3]!=1||!ggml_is_contiguous(tensor)||tensor->nb[1]!=1024*sizeof(float))throw std::runtime_error("Unsupported midlayer token row/type/shape/stride");
            r.norm=tensor;r.frame=c.decode_id;r.byte_offset=size_t(r.input_rows-1)*tensor->nb[1];r.before.resize(1024);ggml_backend_tensor_get(tensor,r.before.data(),r.byte_offset,1024*sizeof(float));double n=0;for(float x:r.before){if(!std::isfinite(x))throw std::runtime_error("Nonfinite midlayer state");n+=double(x)*x;}if(n<=1e-20)throw std::runtime_error("Zero midlayer state");r.before_hash=hash_bytes(r.before.data(),1024*sizeof(float));std::vector<unsigned char> prefix(r.byte_offset);if(!prefix.empty())ggml_backend_tensor_get(tensor,prefix.data(),0,prefix.size());r.prefix_before=hash_bytes(prefix.data(),prefix.size());r.phase="WAIT_CONSUMER";r.hook_events.push_back({{"phase","MIDLAYER_SOURCE_COMPLETED_AND_SYNCHRONIZED"},{"decode_id",c.decode_id},{"row_count",r.input_rows},{"selected_row",r.input_rows-1},{"source_sha256",r.before_hash}});return true;
        }
        if(r.phase!="CONSUMER_ASKED"||tensor->op!=GGML_OP_RMS_NORM||tensor->src[0]!=r.norm||(r.diagnostic&&!r.applied))throw std::runtime_error("Midlayer consumer completed without current source hook");
        r.hook_events.push_back({{"phase","NEXT_LAYER_RMS_COMPLETED"},{"decode_id",c.decode_id}});r.norm=nullptr;r.phase="DONE";return true;
    }catch(const std::exception & e){c.error=e.what();return ask?true:false;}
}
static json receiver_guards(){
    json expected={{"nonce","midlayer-0123456789"},{"model_sha256","m"},{"runner_library_sha256","r"},{"backend_manifest_sha256","b"},{"context_source_sha256","c"},{"token_file_sha256","t"},{"layer_count",14},{"target_layer",6},{"sequence_id",0},{"target_token_position",32},{"decode_epoch",1}};
    json good=expected;good.update({{"schema","V13_AUTHORED_MIDLAYER_EFFECT_VECTOR_V1"},{"scope","AUTHORED_NUMERIC_DIAGNOSTIC"},{"source_id","authored-mid-fixture"},{"target_tensor","l_out-6"},{"target_tensor_before_sha256",std::string(64,'a')},{"dimension",1024},{"architecture","lfm2"},{"next_consumer","norm-7"},{"delta_vector",std::vector<float>(1024,0)}});
    json checks={{"zero_vector_valid",bounded_delta(good,expected).size()==1024}};auto reject=[&](const std::string & key,const json & x){try{bounded_delta(x,expected);checks[key]=false;}catch(const std::exception &){checks[key]=true;}};
    for(auto key:{"nonce","model_sha256","runner_library_sha256","backend_manifest_sha256","context_source_sha256","token_file_sha256","target_tensor","scope","architecture","next_consumer"}){auto x=good;x[key]="wrong";reject(std::string("mismatch_")+key,x);}
    for(auto key:{"layer_count","target_layer","sequence_id","target_token_position","decode_epoch"}){auto x=good;x[key]=true;reject(std::string("bool_")+key,x);x[key]=99;reject(std::string("mismatch_")+key,x);}
    auto x=good;x["delta_vector"]=std::vector<float>(1023,0);reject("wrong_shape",x);x=good;x["delta_vector"][0]=true;reject("bool_coordinate",x);x=good;x["delta_vector"][0]=std::numeric_limits<double>::infinity();reject("nonfinite_coordinate",x);x=good;x["delta_vector"][0]=.126;reject("oversize_norm",x);x=good;x["target_tensor_before_sha256"]="stale";reject("bad_tensor_hash",x);x=good;x["extra"]=1;reject("extra_field",x);x=good;x["delta_vector"]=std::vector<float>(1024,.001f);checks["bounded_nonzero_valid"]=bounded_delta(x,expected).size()==1024;
    Receiver r;r.capture.deadline=Clock::now()-std::chrono::seconds(1);checks["expired_abort"]=receiver_abort(&r);r.capture.deadline=Clock::now()+std::chrono::seconds(1);interrupted=1;checks["cancel_abort"]=receiver_abort(&r);interrupted=0;
    ggml_tensor node{};std::strcpy(node.name,"norm-7");node.ne[1]=33;node.op=GGML_OP_RMS_NORM;
    Receiver stale;stale.capture.active=true;stale.capture.deadline=Clock::now()+std::chrono::seconds(1);stale.armed=true;stale.phase="WAIT_CONSUMER";receiver_callback(&node,true,&stale);checks["stale_consumer_refused_before_write"]=stale.writes==0&&!stale.capture.error.empty();
    try{unique_payload("{\"delta\":1,\"delta\":2}");checks["duplicate_payload_keys_refused"]=false;}catch(const std::exception &){checks["duplicate_payload_keys_refused"]=true;}
    bool pass=std::all_of(checks.begin(),checks.end(),[](const json & v){return v==true;});return {{"schema","V13_MIDLAYER_TYPED_GUARDS_V1"},{"status",pass?"GUARD_PASS":"GUARD_FAIL"},{"checks",checks},{"native_tensor_execution_performed",false}};
}
int main(int argc,char ** argv){
    if(argc==2&&std::string(argv[1])=="--guard-test"){auto g=receiver_guards();std::cout<<g.dump()<<std::endl;return g["status"]=="GUARD_PASS"?0:1;}
    json report={{"schema","V13_BOUNDED_MIDLAYER_EFFECT_DIAGNOSTIC_V1"},{"production_authority",0},{"receiver_authority",0},{"training_authority",0},{"scope","AUTHORED_NUMERIC_DIAGNOSTIC"},{"pid",getpid()}};std::string output;
    try{
        std::map<std::string,std::string> a;for(int i=1;i<argc;i+=2){if(i+1>=argc||std::string(argv[i]).rfind("--",0)!=0||a.count(argv[i]))throw std::runtime_error("Unique --key value required");a[argv[i]]=argv[i+1];}
        const std::set<std::string> keys={"--model","--tokens","--output","--model-sha256","--lib-sha256","--backend-pins","--context-source-sha256","--nonce","--mode","--delta","--delta-sha256"};for(const auto & item:a)if(!keys.count(item.first))throw std::runtime_error("Unknown receiver argument");
        for(auto key:{"--model","--tokens","--output","--model-sha256","--lib-sha256","--backend-pins","--context-source-sha256","--nonce","--mode"})if(!a.count(key))throw std::runtime_error(std::string("Missing ")+key);
        output=a.at("--output");if(a.at("--nonce").size()<16||a.at("--nonce").size()>64||a.at("--context-source-sha256").size()!=64||!std::all_of(a.at("--context-source-sha256").begin(),a.at("--context-source-sha256").end(),[](unsigned char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');}))throw std::runtime_error("Receiver nonce/context SHA bound");auto mode=a.at("--mode");if(mode!="baseline"&&mode!="zero"&&mode!="nonzero")throw std::runtime_error("Receiver mode baseline/zero/nonzero required");
        report["mode"]=mode;report["model"]={{"path",a.at("--model")},{"sha256",sha_file(a.at("--model"))}};report["loaded_llama_library"]=library_identity(reinterpret_cast<const void*>(&llama_decode));report["loaded_ggml_library"]=library_identity(reinterpret_cast<const void*>(&ggml_backend_load_all));report["loaded_ggml_base_library"]=library_identity(reinterpret_cast<const void*>(&ggml_backend_tensor_set));
        if(report["model"]["sha256"]!=a.at("--model-sha256")||report["loaded_llama_library"]["sha256"]!=a.at("--lib-sha256"))throw std::runtime_error("Receiver model/runner SHA mismatch");
        std::ifstream tf(a.at("--tokens"));json input;tf>>input;if(!tf||!input.contains("token_ids")||!input["token_ids"].is_array()||input["token_ids"].empty()||input["token_ids"].size()>128||input.value("context_source_sha256","")!=a.at("--context-source-sha256"))throw std::runtime_error("Receiver exact token/context binding mismatch");
        std::vector<llama_token> tokens;for(const auto & value:input["token_ids"]){if(!value.is_number_integer()||value.is_boolean())throw std::runtime_error("Integer receiver token required");auto id=value.get<int64_t>();if(id<0||id>=65536)throw std::runtime_error("Receiver token outside vocabulary");tokens.push_back(int(id));}report["token_ids"]=tokens;report["token_file_sha256"]=sha_file(a.at("--tokens"));report["context_source_sha256"]=a.at("--context-source-sha256");
        std::string directory=report["loaded_ggml_library"]["path"];directory=directory.substr(0,directory.find_last_of('/'));ggml_backend_load_all_from_path(directory.c_str());std::ifstream pf(a.at("--backend-pins"));json pins;pf>>pins;if(!pf||!pins.contains("libraries"))throw std::runtime_error("Receiver backend pin missing");
        auto verify=[&](const json & id){char path[4096];auto name=id.at("path").get<std::string>();if(!realpath(name.c_str(),path)||!pins["libraries"].contains(path)||pins["libraries"].at(path)!=id.at("sha256"))throw std::runtime_error("Receiver loaded backend/library mismatch");};for(auto key:{"loaded_llama_library","loaded_ggml_library","loaded_ggml_base_library"})verify(report[key]);
        std::ifstream maps("/proc/self/maps");std::string line;std::set<std::string> cpu;while(std::getline(maps,line)){auto p=line.find('/');if(p!=std::string::npos&&line.substr(p).find("/libggml-cpu")!=std::string::npos)cpu.insert(line.substr(p));}if(cpu.empty()||!ggml_backend_reg_count())throw std::runtime_error("Receiver CPU backend unavailable");report["loaded_cpu_backends"]=json::array();for(const auto & p:cpu){json id={{"path",p},{"sha256",sha_file(p)}};verify(id);report["loaded_cpu_backends"].push_back(id);}report["all_loaded_libraries_verified"]=true;
        Receiver r;r.input_rows=int(tokens.size());r.capture.dimension=1024;r.capture.deadline=Clock::now()+std::chrono::seconds(90);r.diagnostic=mode!="baseline";
        if(r.diagnostic){if(!a.count("--delta")||!a.count("--delta-sha256")||sha_file(a.at("--delta"))!=a.at("--delta-sha256"))throw std::runtime_error("Authored delta source SHA mismatch");std::ifstream df(a.at("--delta"));std::string text((std::istreambuf_iterator<char>(df)),{});json delta=unique_payload(text);if(!df)throw std::runtime_error("Malformed typed delta");json expected={{"nonce",a.at("--nonce")},{"model_sha256",a.at("--model-sha256")},{"runner_library_sha256",a.at("--lib-sha256")},{"backend_manifest_sha256",sha_file(a.at("--backend-pins"))},{"context_source_sha256",a.at("--context-source-sha256")},{"token_file_sha256",report["token_file_sha256"]},{"layer_count",14},{"target_layer",6},{"sequence_id",0},{"target_token_position",int(tokens.size()-1)},{"decode_epoch",1}};r.delta=bounded_delta(delta,expected);r.expected_tensor_hash=delta["target_tensor_before_sha256"];report["typed_delta_source"]=delta;report["delta_source_sha256"]=a.at("--delta-sha256");bool allzero=std::all_of(r.delta.begin(),r.delta.end(),[](float x){return x==0;});if((mode=="zero")!=allzero)throw std::runtime_error("Receiver mode/vector zero mismatch");}
        std::signal(SIGINT,signal_handler);std::signal(SIGTERM,signal_handler);llama_backend_init();auto mp=llama_model_default_params();mp.n_gpu_layers=0;std::unique_ptr<llama_model,decltype(&llama_model_free)> model(llama_model_load_from_file(a.at("--model").c_str(),mp),llama_model_free);if(!model||llama_model_n_embd_out(model.get())!=1024||llama_vocab_n_tokens(llama_model_get_vocab(model.get()))!=65536)throw std::runtime_error("Receiver pinned C3 unavailable");
        char arch[32]={0};if(llama_model_meta_val_str(model.get(),"general.architecture",arch,sizeof(arch))<=0||std::strcmp(arch,"lfm2")||llama_model_n_layer(model.get())!=14)throw std::runtime_error("Midlayer requires actual pinned lfm2/14-layer C3");report["actual_architecture"]="lfm2";report["actual_layer_count"]=14;report["target_layer"]=6;report["next_consumer"]="norm-7";report["sequence_id"]=0;report["selected_token_position"]=tokens.size()-1;
        auto cp=llama_context_default_params();cp.n_ctx=2048;cp.n_batch=128;cp.n_ubatch=128;cp.n_seq_max=1;cp.n_threads=2;cp.n_threads_batch=2;cp.embeddings=false;cp.pooling_type=LLAMA_POOLING_TYPE_NONE;cp.attention_type=LLAMA_ATTENTION_TYPE_UNSPECIFIED;cp.offload_kqv=false;cp.op_offload=false;cp.cb_eval=receiver_callback;cp.cb_eval_user_data=&r;cp.abort_callback=receiver_abort;cp.abort_callback_data=&r;
        std::unique_ptr<llama_context,decltype(&llama_free)> ctx(llama_init_from_model(model.get(),cp),llama_free);if(!ctx)throw std::runtime_error("Receiver actual context unavailable");auto batch=llama_batch_init(128,0,1);r.capture.active=true;
        try{for(size_t offset=0;offset<tokens.size();offset+=128){batch.n_tokens=std::min<size_t>(128,tokens.size()-offset);r.armed=offset+batch.n_tokens==tokens.size();for(int i=0;i<batch.n_tokens;++i){batch.token[i]=tokens[offset+i];batch.pos[i]=offset+i;batch.n_seq_id[i]=1;batch.seq_id[i][0]=0;batch.logits[i]=offset+i+1==tokens.size();}++r.capture.decode_id;r.capture.norm_count=r.capture.output_count=0;r.norm=nullptr;int rc=llama_decode(ctx.get(),batch);llama_synchronize(ctx.get());if(rc||receiver_abort(&r))throw std::runtime_error(r.capture.error.empty()?"Receiver actual decode aborted":r.capture.error);}
        if(!r.graph_verified||r.capture.norm_count!=1||r.capture.output_count!=1||(r.diagnostic&&!r.applied))throw std::runtime_error("Receiver effect graph not confirmed");
        report["first_position"]=logits_result(ctx.get(),65536);report["native_state_before"]=r.before;report["native_state_after"]=r.diagnostic?r.after:r.before;report["tensor_before_sha256"]=r.before_hash;report["tensor_after_sha256"]=r.diagnostic?r.after_hash:r.before_hash;report["ephemeral_tensor_writes"]=r.writes;report["actual_update_l2"]=r.update_norm;report["actual_relative_update"]=r.relative_update;report["verified_current_nextlayer_norm_consumes_source"]=r.graph_verified;report["earlier_row_prefix_before_sha256"]=r.prefix_before;report["earlier_row_prefix_after_sha256"]=r.prefix_after;report["final_native_state_after_remaining_layers"]=r.capture.hidden;report["completed_remaining_layers"]=7;report["callback_records"]=r.capture.records;report["hook_events"]=r.hook_events;r.norm=nullptr;r.armed=false;
        }catch(...){llama_batch_free(batch);throw;}llama_batch_free(batch);report["model_sha256_after"]=sha_file(a.at("--model"));if(report["model_sha256_after"]!=a.at("--model-sha256"))throw std::runtime_error("Model weights changed");report["status"]="BOUNDED_MIDLAYER_DIAGNOSTIC_COMPLETE";save_json(output,report);return 0;
    }catch(const std::exception & e){report["status"]="BOUNDED_MIDLAYER_DIAGNOSTIC_FAILED";report["error"]=e.what();if(!output.empty()){try{save_json(output,report);}catch(...) {}}std::cerr<<report.dump()<<std::endl;return 1;}
}
