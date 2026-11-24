import json,sys,time,http.client
sys.path.insert(0,'/home/user/Aii/v13/code')
from v13.cognition import offer_schema
from v13.common import dumps
from v13.runners import wire_json
for _ in range(120):
    try:
        c=http.client.HTTPConnection('127.0.0.1',8977,timeout=5);c.request('GET','/health');r=c.getresponse();r.read()
        if r.status==200:break
    except Exception:pass
    time.sleep(1)
schema=offer_schema(96)
prompt="<|im_start|>user\nOffer help: the user asks how to water tomatoes. Answer as JSON.<|im_end|>\n<|im_start|>assistant\n"
res={'schema_keys':list(schema['properties'])}
for name,ser in (('sorted_common_dumps',dumps),('wire_json',wire_json)):
    c=http.client.HTTPConnection('127.0.0.1',8977,timeout=300)
    c.request('POST','/completion',ser({'prompt':prompt,'json_schema':schema,'n_predict':300,'temperature':0,'seed':1}).encode(),{'Content-Type':'application/json'})
    out=json.loads(c.getresponse().read())['content']
    try:keys=list(json.loads(out))
    except Exception:keys=None
    res[name]={'emitted_key_order':keys,'content':out[:600]}
print(json.dumps(res,indent=1,ensure_ascii=False))
