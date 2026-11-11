"""Read-only model footprint audit. File size is not RAM; no runtime authorization."""
import json
import math
from pathlib import Path

ROLES = {'language':'C3_LANGUAGE','body':'B1_DETAIL','gist':'B2_GIST','needle':'C2_CONTROL'}

def audit(spec, profiles, roles=('language','body','gist','needle')):
    models, entries = spec.get('models'), profiles.get('entries')
    if not isinstance(models,dict) or not isinstance(entries,dict):
        raise ValueError('invalid model/profile schema')
    rows=[]
    for key in roles:
        if key not in ROLES: raise ValueError('unsupported role')
        m=models.get(key)
        if not isinstance(m,dict):
            rows.append({'role':ROLES[key],'status':'MISSING_SPEC'}); continue
        selected=[f for f in (m.get('files') or []) if isinstance(f,dict) and f.get('local_name')==m.get('main_file')]
        if len(selected)!=1:
            rows.append({'role':ROLES[key],'status':'INVALID_MAIN_FILE'}); continue
        f=selected[0]; sha=f.get('sha256'); size=f.get('size')
        if not (isinstance(sha,str) and len(sha)==64 and all(c in '0123456789abcdef' for c in sha)
                and type(size) is int and size>0):
            rows.append({'role':ROLES[key],'status':'INVALID_FILE_METADATA'}); continue
        row={'role':ROLES[key],'model_id':m.get('model_id'),'sha256':sha,
             'file_mib':round(size/1048576,2),'status':'FILE_SIZE_ONLY',
             'resident_mib':None,'redmi_proof':False}
        p=entries.get(sha)
        if isinstance(p,dict):
            n=p.get('size_mib')
            if (p.get('size_bytes')==size and type(n) in (int,float) and math.isfinite(n)
                    and n>0 and p.get('evidence') in
                    ('CLOUD_X86_LOWER_BOUND','HOST_MEASURED_NOT_REDMI','DEVICE_MEASURED')):
                row['resident_mib']=float(n)
                row['status']='PROFILE_'+p['evidence']
                # The source JSON is not authenticated proof of Redmi hardware.
            else: row['status']='PROFILE_REJECTED'
        rows.append(row)
    return {'schema':'v13.model_footprint_audit/1','measurement':'NONE',
            'runtime_admission_authorized':False,'rows':rows}

def main():
    root=Path(__file__).resolve().parents[1]/'specs'
    print(json.dumps(audit(json.loads((root/'models.json').read_text()),
                           json.loads((root/'body-sizes.json').read_text())),indent=2,sort_keys=True))

if __name__=='__main__': main()
