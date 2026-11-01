"""WP-FS7 procedure schema before consolidation (idea: Skill Schema Transport, arXiv 2610.28892; own minimal variant).

An episode is {'text','steps':[{'tool','args'}]}. Consolidating the literal wording stores numbers that will never occur again.
induce() turns episodes into a schema: tool args get slots ({NUMS|op} = all numbers of the question joined by op, {n0},{n1} =
the i-th number) and episodes with the same slotted skeleton are merged; the schema needs >=min_support episodes, else the
skeleton stays a CANDIDATE only. Instantiate fills slots from a NEW question. Declarative only, no code generation.
"""
import re
_NUM=re.compile(r'-?\d+(?:\.\d+)?')

def nums(text):return _NUM.findall(text)
def _slot_str(s,ns):
    found=_NUM.findall(s)
    if found and found==ns and len(ns)>=2:
        sep=_NUM.split(s)[1:-1]
        if len(set(sep))==1 and not _NUM.sub('',s).replace(sep[0],'').strip():return '{NUMS|%s}'%sep[0]
    def r(m):
        v=m.group(0)
        return '{n%d}'%ns.index(v) if v in ns else v
    return _NUM.sub(r,s)
def slotted(ep):
    ns=nums(ep['text']);return [{'tool':st['tool'],'args':{k:(_slot_str(v,ns) if isinstance(v,str) else v) for k,v in st['args'].items()}} for st in ep['steps']]
def induce(episodes,min_support=2):
    groups={}
    for ep in episodes:
        sk=slotted(ep);key=repr(sk)
        g=groups.setdefault(key,{'steps':sk,'support':0,'words':None});g['support']+=1
        w=set(re.findall(r'[a-zA-Z]{3,}',ep['text'].casefold()));g['words']=w if g['words'] is None else g['words']&w
    return [{'steps':g['steps'],'support':g['support'],'trigger':sorted(g['words'] or []),'stage':'SCHEMA' if g['support']>=min_support else 'CANDIDATE'} for g in groups.values()]
def select(schemas,text):
    w=set(re.findall(r'[a-zA-Z]{3,}',text.casefold()));best=None
    for s in schemas:
        if s['stage']!='SCHEMA' or not s['trigger']:continue
        sc=len(set(s['trigger'])&w)/len(s['trigger'])
        if sc>=.6 and (best is None or sc>best[0]):best=(sc,s)
    return best[1] if best else None
def fill(arg,text):
    ns=nums(text)
    def r(m):
        k=m.group(1)
        if k.startswith('NUMS|'):return k[5:].join(ns)
        i=int(k[1:]);
        if i>=len(ns):raise IndexError
        return ns[i]
    return re.sub(r'\{(NUMS\|[^}]*|n\d+)\}',r,arg)
def instantiate(schema,text):
    try:return [{'tool':s['tool'],'args':{k:(fill(v,text) if isinstance(v,str) else v) for k,v in s['args'].items()}} for s in schema['steps']]
    except IndexError:return None
