"""Run268: independent exact-checkout verifier for a current V13-Phone source ZIP.

No model weights or private data may be inside the archive. This is source
packaging integrity, NOT Redmi installation or model/JEPA proof.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

ROOT='V13-Phone/'
REQUIRED=(
    'AGENTS.md','STARTEN.sh','setup.sh','KNOEPFE_EINRICHTEN.sh',
    'v13/runtime.py','v13/models.py','specs/models.json',
    'docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md')
FORBIDDEN_SUFFIX=('.gguf','.safetensors','.sqlite','.sqlite3','.db','.pem','.key','.env','.ggml')
FORBIDDEN_NAMES={'.env','.netrc','credentials.json','token.json'}
MAX_MEMBER=50*1024*1024
MAX_TOTAL=256*1024*1024


def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def sha_zip_member(z,name):
    h=hashlib.sha256()
    with z.open(name) as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def verify(zip_path,root,*,min_files=500):
    zip_path=Path(zip_path);root=Path(root).resolve()
    if not root.is_dir():raise ValueError('missing source root')
    with zipfile.ZipFile(zip_path) as z:
        infos=z.infolist()
        names=[i.filename for i in infos]
        if len(names)!=len(set(names)):raise ValueError('duplicate ZIP member')
        if not names:raise ValueError('empty ZIP')
        total=0
        for i in infos:
            name=i.filename
            parts=PurePosixPath(name).parts
            if (not name.startswith(ROOT) or name.startswith('/') or
                '\\' in name or '..' in parts or not parts or
                any(part in ('','.','..') for part in parts)):
                raise ValueError('unsafe ZIP path')
            if i.is_dir():raise ValueError('directory ZIP member')
            if stat.S_IFMT(i.external_attr>>16)==stat.S_IFLNK:
                raise ValueError('symlink ZIP member')
            if i.file_size>MAX_MEMBER:raise ValueError('oversized ZIP member')
            total+=i.file_size
            if total>MAX_TOTAL:raise ValueError('oversized ZIP payload')
            rel=name[len(ROOT):]
            if rel.lower().endswith(FORBIDDEN_SUFFIX) or PurePosixPath(rel).name.lower() in FORBIDDEN_NAMES:
                raise ValueError('forbidden private/model payload')
            if rel.endswith('.sh') and not (i.external_attr>>16)&0o111:
                raise ValueError('shell launcher not executable')
        manifest_name=ROOT+'WORKSPACE_FILES.json'
        if manifest_name not in names:raise ValueError('missing manifest')
        with z.open(manifest_name) as f:
            data=f.read(5*1024*1024+1)
        if len(data)>5*1024*1024:raise ValueError('manifest too large')
        m=json.loads(data)
        if type(m) is not dict or m.get('schema_version')!=1 or type(m.get('files')) is not dict:
            raise ValueError('invalid manifest schema')
        files=m['files']
        if len(files)<min_files:raise ValueError('source ZIP incomplete')
        if set(names)!={ROOT+k for k in files}|{manifest_name}:
            raise ValueError('manifest member set mismatch')
        for rel in REQUIRED:
            if rel not in files:raise ValueError('missing required source: '+rel)
        if z.testzip() is not None:raise ValueError('ZIP CRC failure')
        for rel,expected in files.items():
            if type(rel) is not str or type(expected) is not str or len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected):
                raise ValueError('invalid manifest digest')
            if sha_zip_member(z,ROOT+rel)!=expected:
                raise ValueError('ZIP member SHA256 mismatch: '+rel)
            p=root/rel
            if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(root):
                raise ValueError('source missing/symlink/escape: '+rel)
            if sha_file(p)!=expected:
                raise ValueError('checkout source SHA256 mismatch: '+rel)
        return {'schema':'V13_RUN268_CURRENT_PHONE_SOURCE_ZIP_V1',
                'evidence_scope':'LINUX_SOFTWARE_SOURCE_PACKAGE_INTEGRITY',
                'zip_sha256':sha_file(zip_path),'file_count':len(files),
                'total_uncompressed_bytes':total,'manifest_sha256':hashlib.sha256(data).hexdigest(),
                'crc':'PASS','all_member_hashes':'PASS','checkout_byte_parity':'PASS',
                'native_model_inference':False,'redmi_measured':False,
                'gates':{'STEP2':'UTILITY_FAIL','B3_L1':'FAIL',
                         'Body_JEPA':'UNAVAILABLE','jepa_weight':0,'V13':'INCOMPLETE'}}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--zip',type=Path,required=True)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result=verify(a.zip,a.root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
