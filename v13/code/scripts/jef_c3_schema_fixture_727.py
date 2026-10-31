"""Run68 registered six-case synthetic JEF/C3 native JSON-schema trial."""
import hashlib
import json

SEED=727
ARMS=('BASELINE','SCHEMA')
MODEL_SHA256='3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d'
RUNNER_SHA256='79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39'
TABLE_SHA256='84f4f482b09310dcde62dfb867078024423886abbcb2740d20e4e6c8747ec7b1'
SCHEMA={'type':'object','properties':{'action':{'type':'string','enum':['A','B','NONE']}},
        'required':['action'],'additionalProperties':False}
TABLE=[
 ('harbor permits','permit fee','credits','review window','cycles','insured',(210,30,True),(155,20,True),(250,14,True),'A'),
 ('museum exhibits','floor area','cells','opening window','slots','accessible',(190,25,False),(220,10,False),(175,18,False),'B'),
 ('robotics workshop','kit cost','tokens','setup window','beats','reusable',(120,15,True),(105,16,True),(110,10,False),'NONE'),
 ('greenhouse sensors','power budget','units','warmup window','steps','shielded',(280,32,False),(200,24,False),(245,19,True),'A'),
 ('library storage','shelf quota','places','transfer window','intervals','covered',(240,25,True),(210,15,False),(230,20,True),'B'),
 ('festival catering','meal allocation','portions','delivery window','ticks','verified',(130,12,False),(135,11,True),(125,13,True),'NONE'),
]


def sha(raw):return hashlib.sha256(raw).hexdigest()


def oracle(rule,options):
    eligible=[(o[0],o[1],name) for name,o in zip('AB',options)
              if o[0]<=rule[0] and o[1]<=rule[1] and (not rule[2] or o[2])]
    return min(eligible)[2] if eligible else 'NONE'


def fixtures():
    if sha(json.dumps(TABLE,sort_keys=True,separators=(',',':')).encode())!=TABLE_SHA256:
        raise ValueError('JEF727_TABLE_CHANGED')
    rows=[]
    for i,item in enumerate(TABLE):
        domain,f1,u1,f2,u2,flag,policy,a,b,action=item
        if oracle(policy,(a,b))!=action:raise ValueError('JEF727_ORACLE_CHANGED')
        project='P2X'+sha(f'JEF727|{SEED}|{i}'.encode())[:16].upper()
        tf=lambda x:'true' if x else 'false'
        current=(f'Project {project}. Choose Option A or Option B using the '
                 f'archived {domain} policy and latest option sheet. '
                 'If neither qualifies, choose NONE.')
        policy_source=(f'Project {project} archived {domain} policy. '
                       f'Maximum {f1}: {policy[0]} {u1}. '
                       f'Maximum {f2}: {policy[1]} {u2}. '
                       f'Required {flag}: {tf(policy[2])}.')
        def opt(label,x):
            return (f'Option {label}: {f1} {x[0]} {u1}; '
                    f'{f2} {x[1]} {u2}; {flag} {tf(x[2])}.')
        sheet_source=(f'Project {project} latest {domain} option sheet. '
                      +opt('A',a)+' '+opt('B',b))
        rows.append({'index':i,'project':project,'domain':domain,'expected':action,
                     'current':current,'policy_source':policy_source,'sheet_source':sheet_source})
    if len({r['project'] for r in rows})!=6 or [r['expected'] for r in rows]!=['A','B','NONE']*2:
        raise ValueError('JEF727_BALANCE_RED')
    return rows


def _unique(pairs):
    out={}
    for k,v in pairs:
        if k in out:raise ValueError('DUPLICATE_JSON_KEY')
        out[k]=v
    return out


def decode_schema(output):
    if type(output) is not str or not 0<len(output.encode('utf-8'))<=1024:
        return None
    try:
        data=json.loads(output,object_pairs_hook=_unique,
                        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE')))
    except (ValueError,TypeError,UnicodeError):
        return None
    if type(data) is not dict or set(data)!={'action'} or type(data['action']) is not str:
        return None
    return data['action'] if data['action'] in ('A','B','NONE') else None


def score(output,expected,arm):
    if expected not in ('A','B','NONE'):raise ValueError('EXPECTED_RED')
    if arm=='BASELINE':return int(type(output) is str and output==expected)
    if arm=='SCHEMA':return int(decode_schema(output)==expected)
    raise ValueError('ARM_RED')
