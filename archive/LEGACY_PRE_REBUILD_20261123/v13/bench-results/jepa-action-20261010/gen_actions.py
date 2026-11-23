import json,subprocess,sys,time,urllib.request
S=sys.argv[1];B=S+'/bench/bin/llama-b10964/';M=S+'/ae/models/language/LFM2.5-350M-QAD-Q4_0.gguf'
P={'translate_de':'Translate this sentence into German. Reply with the German sentence only.',
   'question':'Rewrite this sentence as a yes/no question. Reply with the question only.',
   'negate':'Rewrite this sentence so that it means the opposite (negate it). Reply with the new sentence only.',
   'summarize':'Shorten this sentence to at most four words. Reply with the short version only.'}
d=json.load(open(S+'/jepa/sentences.json'));out={}
p=subprocess.Popen([B+'llama-server','-m',M,'--port','18103','-c','2048','-t','4','--no-webui','--log-disable'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
  for _ in range(240):
    try: urllib.request.urlopen('http://127.0.0.1:18103/health',timeout=1);break
    except OSError: time.sleep(.5)
  t0=time.time()
  for t,ss in d.items():
    for s in ss:
      r={}
      for a,ins in P.items():
        body={'messages':[{'role':'user','content':ins+'\n\n'+s}],'temperature':0,'max_tokens':48}
        req=urllib.request.Request('http://127.0.0.1:18103/v1/chat/completions',json.dumps(body).encode(),{'Content-Type':'application/json'})
        r[a]=json.load(urllib.request.urlopen(req,timeout=120))['choices'][0]['message']['content'].strip().split('\n')[0].strip('"')
      out[s]=r
    print(t,round(time.time()-t0),flush=True)
finally: p.kill();p.wait()
json.dump(out,open(S+'/jepa/actions.json','w'),indent=0,ensure_ascii=False)
