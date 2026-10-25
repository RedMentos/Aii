"""Read-only exact-source LP3 CLI preflight diagnostic; NEVER launches native job."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HELPER_SHA = '05e5bf300f582a03efeaae0133c8e20bf60948a2fa4e05a4867924ac4dc4b831'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def probe(helper, env=None):
    helper=Path(helper)
    if not helper.is_file() or helper.is_symlink() or digest(helper)!=HELPER_SHA:
        raise ValueError('run172_helper_not_exact')
    with tempfile.TemporaryDirectory(prefix='v13-run172-') as root:
        root=Path(root);master=root/'master';master.mkdir()
        candidate=root/'candidate.py';candidate.write_text('print("synthetic-only")\n')
        p=subprocess.run([sys.executable,str(helper),'--master',str(master),'--candidate',str(candidate)],
                         cwd=str(root),env=env if env is not None else os.environ.copy(),
                         text=True,capture_output=True,timeout=20,check=False)
        try:body=json.loads(p.stdout)
        except json.JSONDecodeError:body={}
        expected=(p.returncode==2 and body.get('status')=='BLOCKED' and
                  body.get('native_executed') is False)
        return {'schema':'V13_RUN172_LP3_CLI_DIAGNOSTIC_V1','helper_sha256':HELPER_SHA,
                'returncode':p.returncode,'expected_blocked_rc2':expected,
                'stdout_sha256':hashlib.sha256(p.stdout.encode()).hexdigest(),
                'stderr_sha256':hashlib.sha256(p.stderr.encode()).hexdigest(),
                'stderr_excerpt':p.stderr[:1500],
                'reported_status':body.get('status'),
                'reported_reason':body.get('reason'),
                'native_executed':False,'redmi':False,'body_training_authority':0,
                'gates':{'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE',
                         'jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}}

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: run172_lp3_cli_probe.py EXACT_HELPER')
    r=probe(sys.argv[1]);print(json.dumps(r,indent=2,sort_keys=True))
    raise SystemExit(0 if r['expected_blocked_rc2'] else 1)
