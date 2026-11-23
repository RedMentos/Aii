"""Read-only native evidence exports; not a resumable Runtime/SQLite checkpoint."""
import argparse,hashlib,io,json,os
from pathlib import Path
import zipfile
import numpy as np


def digest(raw):return hashlib.sha256(raw).hexdigest()


def seal(base, destination, minimum=0):
    base,destination=Path(base),Path(destination)
    report=json.loads((base/'cohort/report.json').read_text())
    journal=base/'cohort/rows.jsonl'
    lines=[line for line in journal.read_bytes().splitlines(keepends=True) if line.endswith(b'\n')] if journal.exists() else []
    rows=[json.loads(line) for line in lines]
    if len(rows)<minimum:raise ValueError('Requested prefix is not complete')
    if [r['ordinal'] for r in rows]!=list(range(len(rows))):raise ValueError('Journal ordinals invalid')
    files={}
    def add(name,path):
        path=Path(path)
        if path.is_file():files[name]=path.read_bytes()
    files['rows.jsonl']=b''.join(lines)
    files['rows.json']=(json.dumps(rows,indent=1)+'\n').encode()
    for name in ['report.json','preregistration.json','encoder.json','learn.json','analysis.json','error.txt']:
        add('cohort/'+name,base/'cohort'/name)
    add('wrapper-report.json',base/'wrapper-report.json')
    snapshot=base/'cohort/phase-a-experience'
    if (snapshot/'manifest.json').exists():
        manifest=json.loads((snapshot/'manifest.json').read_text())
        for world,item in manifest['worlds'].items():
            raw=(snapshot/item['file']).read_bytes()
            if digest(raw)!=item['sha256']:raise ValueError('PhaseA snapshot changed')
            files['phase-a-experience/'+item['file']]=raw
        add('phase-a-experience/manifest.json',snapshot/'manifest.json')
    observed_counts={}
    for path in sorted((base/'cohort/home/data/tool_forecast/experience').glob('*.npz')):
        raw=path.read_bytes()
        with np.load(io.BytesIO(raw),allow_pickle=False) as z:observed_counts[path.stem]=len(z['id'])
        files['observed-experience/'+path.name]=raw
    for path in sorted((base/'cohort/home/data/tool_forecast').glob('adapted-*')):
        add('adaptation/'+path.name,path)
    enc=base/'cohort/encoder.json'
    if enc.exists():
        for world,item in json.loads(enc.read_text()).get('retention',{}).items():
            p=Path(item['path'])
            if p.is_file():
                raw=p.read_bytes()
                if digest(raw)!=item['sha256']:raise ValueError('Retention changed')
                files['retention/'+p.name]=raw
    prereg=json.loads((base/'cohort/preregistration.json').read_text())
    tool=Path(prereg['native']['tool_path']);raw=tool.read_bytes()
    if digest(raw)!=prereg['native']['tool_sha256']:raise ValueError('Native tap binary changed')
    files['native/native-layer-taps']=raw
    meta={'schema':'V13_NATIVE_EVIDENCE_SNAPSHOT_V1','rows':len(rows),'observed_status':report['status'],
          'preregistration_sha256':report['preregistration_sha256'],'observed_experience_rows':observed_counts,
          'phase_a_closed':(snapshot/'manifest.json').exists(),
          'terminal_observed':report['status'] in ('ERROR','PARITY_FAIL','CONTINUAL_LEARNING_CONFIRMED','CONTINUAL_LEARNING_NOT_CONFIRMED'),
          'scope':'Read-only byte snapshots; files may span adjacent progress instants. Not a resumable SQLite/Runtime image; no verdict from incomplete rows.'}
    files['snapshot-meta.json']=(json.dumps(meta,indent=1)+'\n').encode()
    files['MANIFEST.json']=(json.dumps({'files':{name:digest(raw) for name,raw in files.items()}},indent=1)+'\n').encode()
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():raise FileExistsError(destination)
    temporary=destination.with_suffix('.partial')
    with zipfile.ZipFile(temporary,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,raw in files.items():z.writestr('V13-Native-Evening/'+name,raw)
    with zipfile.ZipFile(temporary) as z:
        if z.testzip() is not None:raise ValueError('Snapshot ZIP CRC failed')
    with temporary.open('rb') as f:os.fsync(f.fileno())
    os.replace(temporary,destination)
    return meta|{'archive':str(destination.resolve()),'sha256':digest(destination.read_bytes()),'bytes':destination.stat().st_size}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--out',required=True);p.add_argument('--minimum',type=int,default=0);a=p.parse_args()
    print(json.dumps(seal(a.base,a.out,a.minimum)))
