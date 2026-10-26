import json,glob,sys,collections
sys.path[:0]=['.']
from v13.agi import eligibility as E
def guarded(extracted,current,quotes,history,excerpt=240):
    """Exploratory: a rule value counts only if no newer retained exact source (session history excerpt) states another value."""
    rules={k:extracted.get(k) for k in ('budget','deadline','local_only')}
    for k,v in rules.items():
        if v is None or E.stated_values(k,current):continue
        newest=None
        for h in history:  # oldest -> newest
            vals=E.stated_values(k,h[:excerpt])
            if vals:newest=vals
        if newest is not None and v not in newest:rules[k]=None
    opts=[{'entity':o['entity'],'cost':o['cost'],'days':o['days'],'local':o['local']} for o in extracted.get('options',[])]
    return E.decide(rules,opts,current,quotes)['action']
def evaluate(folder):
    c=collections.Counter()
    for tf in sorted(glob.glob(folder+'/tool_*_s*.json')):
        if 'preregistration' in tf:continue
        rep=json.load(open(tf.replace('tool_','step2_')));fx={f['id']:f for f in rep['fixtures']};rows={(r['fixture'],r['variant']):r for r in rep['rows']}
        arm=tf.split('tool_')[1].split('_s')[0]
        for x in json.load(open(tf))['rows']:
            r=rows[(x['fixture'],x['variant'])];ex=(x.get('tool') or {}).get('extracted');f=fx[x['fixture']]
            old=json.loads(x['answer']).get('action') if x.get('answer') else None;ora=f['oracle']['action']
            if ex and r.get('consumer_messages') and len(ex.get('options',[]))==2:
                user=json.loads(next(m['content'] for m in r['consumer_messages'] if m['role']=='user'))
                quotes=[q for a in user.get('analysts',[]) for q in a['verified_quotes']]
                new=guarded(ex,f['current'],quotes,f['history'])
            else:new=old
            for tag,a in (('old',old),('new',new)):
                c[(arm,tag,'exact')]+=a==ora;c[(arm,tag,'wrong')]+=a in ('A','B','NONE') and a!=ora
    return {f'{k[0]}:{k[1]}:{k[2]}':v for k,v in sorted(c.items())}
for f in sys.argv[1:]:print(f,json.dumps(evaluate(f)))
