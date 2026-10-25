"""Run144: independent, non-extracting verifier for exact Run141 phone source ZIP.

Software/packaging integrity only. No model execution, no Redmi evidence.
"""
import argparse
import hashlib
import io
import json
from pathlib import PurePosixPath, Path
import stat
import zipfile

WRAPPER_SHA = '5e95a4a9d2aade9ae213d0f3843148f1f16b181f3805ab0783c82f6e2610d720'
INNER_SHA = '11ea4b19c2be82a219582e877bc671bf6936f8794398dfff4cc92682714c18cd'
RUNTIME_BLOB = 'a691d27bd0772a4fa1f03d57ec90663237bf6825'
INSTALLER_BLOB = '9f9fed1f0fa22f5a2168cc4e41257a2adabd3abd'
INNER_NAME = 'V13-Phone-Run141.zip'
ROOT = 'V13-Phone/'
REQUIRED = ('STARTEN.sh','setup.sh','KNOEPFE_EINRICHTEN.sh','v13/runtime.py',
            'v13/phone_halt.py','tests/test_widget_guide_fallback_run140.py',
            'tests/test_widget_installer_quoting_run127.py',
            'docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md')
FORBIDDEN_SUFFIXES = ('.gguf','.safetensors','.sqlite','.db','.env','.pem','.key')


def sha(data): return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def check_zip(z, expected_names=None):
    names=z.namelist()
    if len(names)!=len(set(names)):raise ValueError('duplicate ZIP member')
    if expected_names is not None and set(names)!=set(expected_names):
        raise ValueError('wrong wrapper members')
    for info in z.infolist():
        name=info.filename; parts=PurePosixPath(name).parts
        if not name or name.startswith('/') or '\\' in name or '..' in parts or parts[0]!='V13-Phone' and expected_names is None:
            raise ValueError('unsafe ZIP member path')
        if stat.S_IFMT(info.external_attr>>16)==stat.S_IFLNK:
            raise ValueError('ZIP symlink')
        if info.file_size>40*1024*1024:raise ValueError('oversized ZIP member')
    if z.testzip() is not None:raise ValueError('CRC failure')


def verify(wrapper_bytes,expected_wrapper=WRAPPER_SHA,expected_inner=INNER_SHA):
    if sha(wrapper_bytes)!=expected_wrapper:raise ValueError('wrapper SHA256 mismatch')
    with zipfile.ZipFile(io.BytesIO(wrapper_bytes)) as outer:
        check_zip(outer,[INNER_NAME])
        inner_bytes=outer.read(INNER_NAME)
    if sha(inner_bytes)!=expected_inner:raise ValueError('inner SHA256 mismatch')
    with zipfile.ZipFile(io.BytesIO(inner_bytes)) as z:
        check_zip(z)
        names=set(z.namelist())
        for name in REQUIRED:
            if ROOT+name not in names:raise ValueError('missing required source '+name)
        for name in names:
            if name.lower().endswith(FORBIDDEN_SUFFIXES):raise ValueError('forbidden model/private payload')
        manifest=json.loads(z.read(ROOT+'WORKSPACE_FILES.json'))
        if manifest.get('schema_version')!=1 or not isinstance(manifest.get('files'),dict):
            raise ValueError('invalid manifest')
        files=manifest['files']
        if len(files)!=867 or set(ROOT+x for x in files)|{ROOT+'WORKSPACE_FILES.json'}!=names:
            raise ValueError('manifest/file-set mismatch')
        for path,digest in files.items():
            if not isinstance(digest,str) or len(digest)!=64 or sha(z.read(ROOT+path))!=digest:
                raise ValueError('manifest SHA256 mismatch '+path)
        if git_blob(z.read(ROOT+'v13/runtime.py'))!=RUNTIME_BLOB:
            raise ValueError('frozen Runtime blob mismatch')
        if git_blob(z.read(ROOT+'KNOEPFE_EINRICHTEN.sh'))!=INSTALLER_BLOB:
            raise ValueError('Widget installer blob mismatch')
    return {'schema':'V13_RUN144_PHONE_ZIP_READONLY_V1','evidence_class':'LINUX_SOFTWARE_SOURCE_ZIP_INTEGRITY',
            'source_head':'fe902a560ea8bff171ff3b8c4b134bb9b0366211',
            'wrapper_sha256':sha(wrapper_bytes),'inner_sha256':sha(inner_bytes),
            'manifest_count':len(files),'crc':'PASS','file_hashes':'PASS',
            'runtime_blob':RUNTIME_BLOB,'installer_blob':INSTALLER_BLOB,
            'redmi':'NOT_RUN','native_models':'NOT_RUN',
            'gates':{'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE',
                     'jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'},
            'claim_limit':'SOURCE_ARCHIVE_INTEGRITY_ONLY_NOT_PHONE_RUNTIME_PROOF'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--wrapper',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=verify(a.wrapper.read_bytes())
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
