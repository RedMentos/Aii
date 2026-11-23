// One bounded pause/resume diagnostic on the existing read-only BodyPort.
// Reuse the established observer unchanged; no production or approval authority.
#define main v13_established_observer_main
#include "native_prefill_worker.cpp"
#undef main
#include <poll.h>
#include <cerrno>
#include <cstdlib>

static bool sha_string(const std::string & value) {
    return value.size()==64 && std::all_of(value.begin(),value.end(),[](unsigned char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');});
}
static std::string sha_string_bytes(const std::string & value) {
    sha256_t state;sha256_init(&state);sha256_update(&state,reinterpret_cast<const unsigned char*>(value.data()),value.size());
    unsigned char digest[32];sha256_final(&state,digest);std::ostringstream out;
    for(auto c:digest)out<<std::hex<<std::setw(2)<<std::setfill('0')<<int(c);
    return out.str();
}
static json unique_json(const std::string & text) {
    std::vector<std::set<std::string>> keys;
    auto callback=[&](int,json::parse_event_t event,json & value){
        if(event==json::parse_event_t::object_start)keys.emplace_back();
        if(event==json::parse_event_t::key && !keys.back().insert(value.get<std::string>()).second)throw std::runtime_error("Duplicate command JSON key");
        if(event==json::parse_event_t::object_end)keys.pop_back();
        return true;
    };
    return json::parse(text,callback);
}
static std::vector<std::pair<int,double>> validate_resume(const json & command,const json & handle,bool already_claimed,bool expired) {
    if(already_claimed)throw std::runtime_error("Handle already consumed; duplicate resume refused");
    if(expired)throw std::runtime_error("Expired prefill handle");
    if(!command.is_object()||command.size()!=5)throw std::runtime_error("Resume command requires exactly five fields");
    for(const auto * key:{"command","handle_id","nonce","context_source_sha256","bias"})if(!command.contains(key))throw std::runtime_error("Missing resume field");
    for(const auto * key:{"command","handle_id","nonce","context_source_sha256"})if(!command.at(key).is_string())throw std::runtime_error("Resume binding must be a string");
    if(command.at("command")!="resume"||command.at("handle_id")!=handle.at("handle_id")||command.at("nonce")!=handle.at("nonce")||command.at("context_source_sha256")!=handle.at("context_source_sha256"))throw std::runtime_error("Stale/mismatched prefill handle");
    const auto & rows=command.at("bias");if(!rows.is_array()||rows.size()>16)throw std::runtime_error("At most16 native vocabulary bias rows permitted");
    std::vector<std::pair<int,double>> result;std::set<int> seen;
    for(const auto & row:rows){
        if(!row.is_array()||row.size()!=2||!row[0].is_number_integer()||row[0].is_boolean()||!row[1].is_number()||row[1].is_boolean())throw std::runtime_error("Bias requires exact integer token ID and finite numeric value");
        auto id=row[0].get<int64_t>();double value=row[1].get<double>();
        if(id<0||id>=65536||!std::isfinite(value)||std::abs(value)>12||!seen.insert(int(id)).second)throw std::runtime_error("Invalid/nonfinite/duplicate/out-of-range native bias");
        result.emplace_back(int(id),value);
    }
    return result;
}
static std::string read_bounded_command(Clock::time_point deadline,Capture & capture) {
    std::string line;
    while(true){
        if(interrupted||Clock::now()>=deadline||abort_compute(&capture))throw std::runtime_error("Prefill wait cancelled/deadline/expired");
        pollfd p{STDIN_FILENO,POLLIN,0};int rc=poll(&p,1,50);
        if(rc<0){if(errno==EINTR)continue;throw std::runtime_error("Command poll failed");}
        if(rc==0)continue;
        if(!(p.revents&POLLIN))throw std::runtime_error("Command input closed before resume");
        char c;auto n=read(STDIN_FILENO,&c,1);if(n!=1)throw std::runtime_error("Command input closed before resume");
        if(c=='\n')return line;
        line.push_back(c);if(line.size()>16384)throw std::runtime_error("Command exceeds16KiB bound");
    }
}
static json guard_checks() {
    json handle={{"handle_id",std::string(64,'a')},{"nonce","0123456789abcdef"},{"context_source_sha256",std::string(64,'b')}};
    json good={{"command","resume"},{"handle_id",handle["handle_id"]},{"nonce",handle["nonce"]},{"context_source_sha256",handle["context_source_sha256"]},{"bias",json::array()}};
    json checks=json::object();checks["zero_bias_valid"]=validate_resume(good,handle,false,false).empty();
    auto reject=[&](const std::string & name,json cmd,bool claimed=false,bool expired=false){try{validate_resume(cmd,handle,claimed,expired);checks[name]=false;}catch(const std::exception &){checks[name]=true;}};
    reject("duplicate_claim_refused",good,true);reject("expired_handle_refused",good,false,true);
    for(auto key:{"handle_id","nonce","context_source_sha256"}){auto c=good;c[key]="stale";reject(std::string("mismatched_")+key,c);}
    auto c=good;c["bias"]={{true,1.}};reject("bool_token_refused",c);c["bias"]={{1,true}};reject("bool_bias_refused",c);
    c["bias"]={{-1,1.}};reject("negative_id_refused",c);c["bias"]={{65536,1.}};reject("large_id_refused",c);
    c["bias"]={{1,12.01}};reject("large_bias_refused",c);c["bias"]={{1,std::numeric_limits<double>::infinity()}};reject("nonfinite_bias_refused",c);
    c["bias"]={{1,1.},{1,2.}};reject("duplicate_row_refused",c);c["bias"]=json::array();for(int i=0;i<17;++i)c["bias"].push_back({i,1.});reject("row_limit_refused",c);
    c=good;c["extra"]=1;reject("extra_field_refused",c);c=good;c.erase("nonce");reject("missing_field_refused",c);
    try{unique_json("{\"command\":1,\"command\":2}");checks["duplicate_json_key_refused"]=false;}catch(const std::exception &){checks["duplicate_json_key_refused"]=true;}
    try{unique_json("{bad}");checks["malformed_json_refused"]=false;}catch(const std::exception &){checks["malformed_json_refused"]=true;}
    c=good;c["bias"]={{0,-12.},{65535,12.}};checks["valid_boundary_rows"]=validate_resume(c,handle,false,false).size()==2;
    bool pass=std::all_of(checks.begin(),checks.end(),[](const json & x){return x==true;});
    return {{"schema","V13_PREFILL_SESSION_GUARDS_V1"},{"status",pass?"GUARD_PASS":"GUARD_FAIL"},{"checks",checks},{"native_inference_performed",false}};
}
int main(int argc,char ** argv) {
    if(argc==2 && std::string(argv[1])=="--guard-test"){auto r=guard_checks();std::cout<<r.dump()<<std::endl;return r["status"]=="GUARD_PASS"?0:1;}
    json report={{"schema","V13_CAUSAL_PREFILL_SESSION_DIAGNOSTIC_V1"},{"production_integration",false},{"training_authority",0},{"approval_authority",0},{"receiver_authority",0},{"pid",getpid()},{"resume_decode_calls",0},{"resume_prefill_calls",0},{"handle_consumed",false}};
    std::string output;
    try {
        std::map<std::string,std::string> a;
        for(int i=1;i<argc;i+=2){if(i+1>=argc||std::string(argv[i]).rfind("--",0)!=0||a.count(argv[i]))throw std::runtime_error("Expected unique --key value");a[argv[i]]=argv[i+1];}
        for(auto key:{"--model","--tokens","--output","--features","--model-sha256","--lib-sha256","--backend-pins","--context-source-sha256","--nonce"})if(!a.count(key))throw std::runtime_error(std::string("Missing ")+key);
        const std::set<std::string> allowed={"--model","--tokens","--output","--features","--model-sha256","--lib-sha256","--backend-pins","--context-source-sha256","--nonce","--wait-seconds","--seconds"};
        for(const auto & item:a)if(!allowed.count(item.first))throw std::runtime_error("Unknown session argument");
        output=a.at("--output");if(!sha_string(a.at("--context-source-sha256"))||a.at("--nonce").size()<16||a.at("--nonce").size()>64)throw std::runtime_error("Bounded context SHA/nonce required");
        auto bounded_integer=[&](const char * key,int fallback,int low,int high){if(!a.count(key))return fallback;size_t used=0;int n=std::stoi(a.at(key),&used);if(used!=a.at(key).size()||n<low||n>high)throw std::runtime_error("Session integer bound");return n;};
        int wait_seconds=bounded_integer("--wait-seconds",15,1,30),seconds=bounded_integer("--seconds",90,5,120);
        std::ifstream f(a.at("--tokens"));json input;f>>input;if(!f||!input.contains("token_ids")||!input["token_ids"].is_array()||input["token_ids"].empty()||input["token_ids"].size()>512)throw std::runtime_error("Bounded exact token input required");
        std::vector<llama_token> tokens;for(const auto & v:input["token_ids"]){if(!v.is_number_integer()||v.is_boolean())throw std::runtime_error("Exact native token ID required");auto id=v.get<int64_t>();if(id<0||id>=65536)throw std::runtime_error("Native token outside vocabulary");tokens.push_back(int(id));}
        if(!input.contains("context_source_sha256")||input["context_source_sha256"]!=a.at("--context-source-sha256"))throw std::runtime_error("Token/context source binding mismatch");
        report["token_ids"]=tokens;report["token_file_sha256"]=sha_file(a.at("--tokens"));report["context_source_sha256"]=a.at("--context-source-sha256");
        report["model"]={{"path",a.at("--model")},{"sha256",sha_file(a.at("--model"))}};
        report["loaded_llama_library"]=library_identity(reinterpret_cast<const void*>(&llama_decode));report["loaded_ggml_base_library"]=library_identity(reinterpret_cast<const void*>(&ggml_backend_tensor_get));report["loaded_ggml_library"]=library_identity(reinterpret_cast<const void*>(&ggml_backend_load_all));
        if(report["model"]["sha256"]!=a.at("--model-sha256")||report["loaded_llama_library"]["sha256"]!=a.at("--lib-sha256"))throw std::runtime_error("Model/runner SHA mismatch");
        std::string directory=report["loaded_ggml_library"]["path"];directory=directory.substr(0,directory.find_last_of('/'));ggml_backend_load_all_from_path(directory.c_str());
        std::ifstream pin_file(a.at("--backend-pins"));json pins;pin_file>>pins;if(!pin_file||!pins.contains("libraries"))throw std::runtime_error("Library pin manifest missing");
        auto verify=[&](const json & identity){char resolved[4096];auto path=identity.at("path").get<std::string>();if(!realpath(path.c_str(),resolved)||!pins["libraries"].contains(resolved)||pins["libraries"].at(resolved)!=identity.at("sha256"))throw std::runtime_error("Loaded library/backend pin mismatch");};
        for(const auto * key:{"loaded_llama_library","loaded_ggml_library","loaded_ggml_base_library"})verify(report[key]);
        report["loaded_cpu_backend_libraries"]=json::array();std::ifstream maps("/proc/self/maps");std::string line;std::set<std::string> cpu;
        while(std::getline(maps,line)){auto slash=line.find('/');if(slash!=std::string::npos&&line.substr(slash).find("/libggml-cpu")!=std::string::npos)cpu.insert(line.substr(slash));}
        if(cpu.empty()||ggml_backend_reg_count()==0)throw std::runtime_error("No actual loaded CPU backend");
        for(const auto & path:cpu){json id={{"path",path},{"sha256",sha_file(path)}};verify(id);report["loaded_cpu_backend_libraries"].push_back(id);}report["all_loaded_libraries_verified"]=true;
        report["backend_pins_sha256"]=sha_file(a.at("--backend-pins"));
        std::signal(SIGINT,signal_handler);std::signal(SIGTERM,signal_handler);Capture capture;capture.deadline=Clock::now()+std::chrono::seconds(seconds);
        llama_backend_init();auto mp=llama_model_default_params();mp.n_gpu_layers=0;
        std::unique_ptr<llama_model,decltype(&llama_model_free)> model(llama_model_load_from_file(a.at("--model").c_str(),mp),llama_model_free);if(!model)throw std::runtime_error("Actual model load failed");
        capture.dimension=llama_model_n_embd_out(model.get());if(capture.dimension!=1024||llama_vocab_n_tokens(llama_model_get_vocab(model.get()))!=65536)throw std::runtime_error("Pinned C3 dimension/vocabulary mismatch");
        auto cp=llama_context_default_params();cp.n_ctx=2048;cp.n_batch=128;cp.n_ubatch=128;cp.n_seq_max=1;cp.n_threads=2;cp.n_threads_batch=2;cp.embeddings=false;cp.pooling_type=LLAMA_POOLING_TYPE_NONE;cp.attention_type=LLAMA_ATTENTION_TYPE_UNSPECIFIED;cp.offload_kqv=false;cp.op_offload=false;cp.abort_callback=abort_compute;cp.abort_callback_data=&capture;cp.cb_eval=observe;cp.cb_eval_user_data=&capture;
        std::unique_ptr<llama_context,decltype(&llama_free)> ctx(llama_init_from_model(model.get(),cp),llama_free);if(!ctx)throw std::runtime_error("Actual context creation failed");
        auto batch=llama_batch_init(128,0,1);capture.active=true;json prefill_calls=json::array();
        try {
            for(size_t offset=0;offset<tokens.size();offset+=128){batch.n_tokens=std::min<size_t>(128,tokens.size()-offset);for(int i=0;i<batch.n_tokens;++i){batch.token[i]=tokens[offset+i];batch.pos[i]=offset+i;batch.n_seq_id[i]=1;batch.seq_id[i][0]=0;batch.logits[i]=offset+i+1==tokens.size();}++capture.decode_id;capture.norm_count=capture.output_count=0;capture.hidden.clear();int rc=llama_decode(ctx.get(),batch);llama_synchronize(ctx.get());prefill_calls.push_back({{"offset",offset},{"tokens",batch.n_tokens},{"return_code",rc}});if(rc||abort_compute(&capture))throw std::runtime_error("Actual causal prefill failed/aborted");}
            if(capture.norm_count!=1||capture.output_count!=1||capture.hidden.size()!=1024)throw std::runtime_error("Actual same-prefill state/logit capture missing");
            json first=logits_result(ctx.get(),65536);report["prefill_decode_calls"]=prefill_calls;
            json features={{"schema","V13_PAUSED_CAUSAL_PREFILL_FEATURES_V1"},{"pid",getpid()},{"token_ids",tokens},{"live_last_state",capture.hidden},{"first_position",first},{"context_source_sha256",a.at("--context-source-sha256")},{"model_sha256",report["model"]["sha256"]},{"lib_sha256",report["loaded_llama_library"]["sha256"]}};save_json(a.at("--features"),features);
            auto expiry=std::min(capture.deadline,Clock::now()+std::chrono::seconds(wait_seconds));
            json handle={{"schema","V13_CAUSAL_PREFILL_HANDLE_V1"},{"nonce",a.at("--nonce")},{"pid",getpid()},{"model_sha256",report["model"]["sha256"]},{"lib_sha256",report["loaded_llama_library"]["sha256"]},{"backend_pins_sha256",report["backend_pins_sha256"]},{"token_file_sha256",report["token_file_sha256"]},{"context_source_sha256",a.at("--context-source-sha256")},{"features_sha256",sha_file(a.at("--features"))},{"sequence_id",0},{"next_position",tokens.size()},{"context_tokens",2048},{"prefill_generation",1},{"wait_ttl_seconds",wait_seconds}};
            handle["handle_id"]=sha_string_bytes(handle.dump());report["handle"]=handle;report["status"]="PREFILLED_WAITING_ONE_COMMAND";save_json(output,report);
            std::cout<<json({{"status","PREFILLED_READY"},{"handle",handle},{"features_path",a.at("--features")}}).dump()<<std::endl;
            auto command=unique_json(read_bounded_command(expiry,capture));auto rows=validate_resume(command,handle,false,Clock::now()>=expiry);
            report["handle_consumed"]=true;report["accepted_command"]=command;std::vector<float> biased=first["logits"].get<std::vector<float>>();for(const auto & row:rows)biased[row.first]+=float(row.second);
            int next=int(std::max_element(biased.begin(),biased.end())-biased.begin());report["first_native_greedy_token_id"]=first["greedy_token_id"];report["first_biased_token_id"]=next;report["bias_applied_positions"]=rows.empty()?0:1;report["continuation"]=json::array();std::vector<int> generated={next};
            for(int i=0;i<3;++i){batch.n_tokens=1;batch.token[0]=next;batch.pos[0]=tokens.size()+i;batch.n_seq_id[0]=1;batch.seq_id[0][0]=0;batch.logits[0]=1;++capture.decode_id;capture.norm_count=capture.output_count=0;capture.hidden.clear();int rc=llama_decode(ctx.get(),batch);llama_synchronize(ctx.get());report["resume_decode_calls"]=i+1;if(rc||abort_compute(&capture)||capture.norm_count!=1||capture.output_count!=1)throw std::runtime_error("Actual unbiased continuation decode failed/aborted");auto step=logits_result(ctx.get(),65536);report["continuation"].push_back({{"input_token_id",next},{"position",batch.pos[0]},{"greedy_next_token_id",step["greedy_token_id"]},{"bias_applied",false}});next=step["greedy_token_id"];generated.push_back(next);}
            std::string preview;const auto * vocab=llama_model_get_vocab(model.get());for(auto token:generated){std::vector<char> piece(128);int n=llama_token_to_piece(vocab,token,piece.data(),piece.size(),0,false);if(n<0){piece.resize(-n);n=llama_token_to_piece(vocab,token,piece.data(),piece.size(),0,false);}if(n<0)throw std::runtime_error("Actual native token decode failed");preview.append(piece.data(),size_t(n));}
            report["decoded_native_token_ids"]=generated;report["decoded_native_preview"]=preview;report["callback_records"]=capture.records;report["unbiased_continuation_steps"]=3;report["same_context_lifetime"]=true;report["additional_commands_accepted"]=0;report["status"]="PAUSE_RESUME_DIAGNOSTIC_COMPLETE";
        } catch(...){llama_batch_free(batch);throw;}llama_batch_free(batch);save_json(output,report);std::cout<<json({{"status",report["status"]},{"handle_consumed",true}}).dump()<<std::endl;return 0;
    } catch(const std::exception & exc){report["status"]="PAUSE_RESUME_DIAGNOSTIC_FAILED";report["error"]=exc.what();if(!output.empty()){try{save_json(output,report);}catch(...) {}}std::cerr<<report.dump()<<std::endl;return 1;}
}
