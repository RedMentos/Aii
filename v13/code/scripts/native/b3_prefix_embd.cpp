// WP-Z4b B3 L2 prefix SHADOW runner: K continuous prefix vectors -> receiver native input path (llama.cpp batch.embd),
// then the text tokens; returns the mean of the receiver's final per-token states over the TEXT tokens only (prefix
// positions excluded), so any prefix effect must pass through the frozen receiver backbone.
// Research tool only: no runtime path uses it, LATENT authority stays 0.
//
// Build (headers from the llama.cpp b10964 source tarball, linked against the b10964 release libllama.so):
//   g++ -O2 -std=c++17 -I<src>/include -I<src>/ggml/include b3_prefix_embd.cpp -L<bin> -lllama -lggml -lggml-base -o b3_prefix_embd
// Usage: GGML_BACKEND_DIR=<bin> b3_prefix_embd <model.gguf> <jobs.bin> <out.bin> [threads]
//        b3_prefix_embd <model.gguf> --tokenize   (stdin: one text per line, \n escaped as \\n; stdout: token ids per line)
// jobs.bin: u32 n_items, u32 n_embd; per item: u32 n_prefix, f32[n_prefix*n_embd], u32 n_bytes, utf8 text
// out.bin : u32 n_items, u32 n_embd; per item: u32 n_text_tokens, f32[n_embd] (unnormalized mean over text tokens)
#include "llama.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

static uint32_t rd32(FILE *f){uint32_t v;if(fread(&v,4,1,f)!=1){fprintf(stderr,"short read\n");exit(2);}return v;}

int main(int argc,char **argv){
    if(argc<3||(argc<4&&std::string(argv[2])!="--tokenize")){fprintf(stderr,"usage: %s model jobs out [threads]\n",argv[0]);return 1;}
    int threads=argc>4?atoi(argv[4]):4;
    llama_log_set([](ggml_log_level l,const char *t,void *){if(l>=GGML_LOG_LEVEL_ERROR)fputs(t,stderr);},nullptr);
    // CPU backend variants live next to libllama.so in the release package
    if(const char *dir=getenv("GGML_BACKEND_DIR"))ggml_backend_load_all_from_path(dir);else ggml_backend_load_all();
    llama_model_params mp=llama_model_default_params();mp.n_gpu_layers=0;
    llama_model *model=llama_model_load_from_file(argv[1],mp);
    if(!model){fprintf(stderr,"load failed\n");return 1;}
    const llama_vocab *vocab=llama_model_get_vocab(model);
    if(std::string(argv[2])=="--tokenize"){
        std::vector<llama_token> ids(8192);char *line=nullptr;size_t cap=0;ssize_t n;
        while((n=getline(&line,&cap,stdin))>0){
            std::string t(line,n);if(!t.empty()&&t.back()=='\n')t.pop_back();
            for(size_t p=0;(p=t.find("\\n",p))!=std::string::npos;)t.replace(p,2,"\n");
            int nt=llama_tokenize(vocab,t.c_str(),(int)t.size(),ids.data(),(int)ids.size(),true,true);
            for(int i=0;i<nt;++i)printf(i?" %d":"%d",ids[i]);printf("\n");
        }
        free(line);llama_model_free(model);return 0;
    }
    const int n_embd=llama_model_n_embd(model),n_inp=llama_model_n_embd_inp(model);
    const llama_rope_type rt=llama_model_rope_type(model);
    const int n_pos=(rt==LLAMA_ROPE_TYPE_MROPE||rt==LLAMA_ROPE_TYPE_IMROPE)?4:1;
    llama_context_params cp=llama_context_default_params();
    cp.n_ctx=2048;cp.n_batch=512;cp.n_ubatch=512;cp.n_threads=threads;cp.n_threads_batch=threads;
    cp.embeddings=true;cp.pooling_type=LLAMA_POOLING_TYPE_NONE;cp.no_perf=true;
    llama_context *ctx=llama_init_from_model(model,cp);
    if(!ctx){fprintf(stderr,"ctx failed\n");return 1;}
    FILE *fi=fopen(argv[2],"rb");if(!fi){perror("jobs");return 1;}
    uint32_t n_items=rd32(fi),d=rd32(fi);
    if((int)d!=n_inp){fprintf(stderr,"jobs n_embd %u != model n_embd_inp %d\n",d,n_inp);return 1;}
    FILE *fo=fopen(argv[3],"wb");uint32_t ne=n_embd;fwrite(&n_items,4,1,fo);fwrite(&ne,4,1,fo);
    fprintf(stderr,"n_embd=%d n_embd_inp=%d rope_type=%d n_pos=%d add_bos=%d items=%u\n",n_embd,n_inp,(int)rt,n_pos,(int)llama_vocab_get_add_bos(vocab),n_items);
    std::vector<float> pre,mean(n_embd);std::vector<llama_token> tok(4096);
    for(uint32_t it=0;it<n_items;++it){
        uint32_t k=rd32(fi);pre.resize((size_t)k*d);
        if(k&&fread(pre.data(),4,pre.size(),fi)!=pre.size()){fprintf(stderr,"short prefix\n");return 2;}
        uint32_t nb=rd32(fi);std::string text(nb,'\0');if(nb&&fread(&text[0],1,nb,fi)!=nb){fprintf(stderr,"short text\n");return 2;}
        int nt=llama_tokenize(vocab,text.c_str(),(int)text.size(),tok.data(),(int)tok.size(),true,true);
        if(nt<=0){fprintf(stderr,"tokenize failed item %u\n",it);return 2;}
        llama_memory_clear(llama_get_memory(ctx),true);
        // leading special tokens (BOS if the vocab adds one) stay before the prefix, the text follows it
        int lead=(llama_vocab_get_add_bos(vocab)&&tok[0]==llama_vocab_bos(vocab))?1:0;int pos0=0;
        if(lead){
            llama_batch b=llama_batch_get_one(tok.data(),1);
            if(llama_decode(ctx,b)){fprintf(stderr,"decode bos failed\n");return 3;}pos0=1;
        }
        if(k){
            llama_batch b=llama_batch_init((int)k,(int)d,1);b.n_tokens=(int)k;
            memcpy(b.embd,pre.data(),pre.size()*4);
            std::vector<llama_pos> pp((size_t)k*n_pos);
            for(int j=0;j<n_pos;++j)for(uint32_t i=0;i<k;++i)pp[(size_t)j*k+i]=pos0+(llama_pos)i;
            llama_pos *saved=b.pos;b.pos=pp.data();
            for(uint32_t i=0;i<k;++i){b.n_seq_id[i]=1;b.seq_id[i][0]=0;b.logits[i]=0;}
            int rc=llama_decode(ctx,b);b.pos=saved;llama_batch_free(b);
            if(rc){fprintf(stderr,"decode prefix failed item %u rc %d\n",it,rc);return 3;}
            pos0+=(int)k;
        }
        int n_text=nt-lead;
        llama_batch b=llama_batch_init(n_text,0,1);b.n_tokens=n_text;
        for(int i=0;i<n_text;++i){b.token[i]=tok[lead+i];b.pos[i]=pos0+i;b.n_seq_id[i]=1;b.seq_id[i][0]=0;b.logits[i]=1;}
        if(llama_decode(ctx,b)){fprintf(stderr,"decode text failed item %u\n",it);return 3;}
        std::fill(mean.begin(),mean.end(),0.f);
        for(int i=0;i<n_text;++i){const float *e=llama_get_embeddings_ith(ctx,i);for(int j=0;j<n_embd;++j)mean[j]+=e[j];}
        for(int j=0;j<n_embd;++j)mean[j]/=n_text;
        llama_batch_free(b);
        uint32_t u=(uint32_t)n_text;fwrite(&u,4,1,fo);fwrite(mean.data(),4,n_embd,fo);
    }
    fclose(fo);fclose(fi);llama_free(ctx);llama_model_free(model);return 0;
}
