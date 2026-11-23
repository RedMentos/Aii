import json,subprocess,sys,time,urllib.request
S=sys.argv[1];B=S+'/bench/bin/llama-b10964/';M=S+'/ae/models/language/LFM2.5-350M-QAD-Q4_0.gguf'
Q=['What is the name of my cat?','Where do I work?','What is my favourite colour?','What is the name of my brother?']
p=subprocess.Popen([B+'llama-server','-m',M,'--port','18104','-c','2048','-t','2','--no-webui','--log-disable'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);out={}
try:
  for _ in range(240):
    try: urllib.request.urlopen('http://127.0.0.1:18104/health',timeout=1);break
    except OSError: time.sleep(.5)
  for q in Q:
    vs=[]
    for i in range(12):
      body={'messages':[{'role':'user','content':'Reword this question in a different way. Reply with the new question only.\n\n'+q}],'temperature':1.0,'seed':100+i,'max_tokens':32}
      req=urllib.request.Request('http://127.0.0.1:18104/v1/chat/completions',json.dumps(body).encode(),{'Content-Type':'application/json'})
      vs.append(json.load(urllib.request.urlopen(req,timeout=120))['choices'][0]['message']['content'].strip().split('\n')[0].strip('"'))
    out[q]=vs
finally: p.kill();p.wait()
json.dump(out,open(S+'/jepa/dreams.json','w'),indent=1)
print(json.dumps(out,indent=1))
