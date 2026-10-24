import hashlib
import json
import tempfile
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import z6b_offpolicy_wake as Z

def fixture():
    rows=[]
    for arm in Z.ARMS:
        for i in range(60):
            wrong=i==0
            text='57 + 19 + 38 = 94 euros' if wrong else '87 + 51 + 66 = 204 euros'
            rows.append({'arm':arm,'fixture':f'summary{i:02}', 'output':text,
                         'pass':(i!=0 if arm=='disabled' else True),'turn_s':2. if arm=='disabled' else 5.})
    return {'kind':'V13_Z6A_EFFORT_BENCH','seed':23,'rows':rows}

class OffPolicyTests(unittest.TestCase):
    def test_only_disabled_text_selects(self):
        d=fixture();r=Z.analyse(d)
        self.assertEqual(r['wakes'],1);self.assertEqual(r['gains'],1)
        self.assertEqual(r['selected_pass'],60)
        self.assertFalse(r['canonical_gate_pass'])
    def test_adaptive_text_never_selects(self):
        d=fixture();a=Z.analyse(d)
        for row in d['rows']:
            if row['arm']=='adaptive':row['output']='100 + 200 = 1'
        b=Z.analyse(d)
        self.assertEqual([x['selected_arm'] for x in a['decisions']],
                         [x['selected_arm'] for x in b['decisions']])
    def test_label_leak_not_used_to_select(self):
        d=fixture();a=Z.analyse(d)
        for row in d['rows']:row['pass']=not row['pass']
        b=Z.analyse(d)
        self.assertEqual([x['selected_arm'] for x in a['decisions']],
                         [x['selected_arm'] for x in b['decisions']])
    def test_duplicate_row_fails(self):
        d=fixture();d['rows'][1]['fixture']=d['rows'][0]['fixture']
        with self.assertRaises(ValueError):Z.analyse(d)
    def test_missing_arm_row_fails(self):
        d=fixture();d['rows'].pop()
        with self.assertRaises(ValueError):Z.analyse(d)
    def test_bad_pass_type_fails(self):
        d=fixture();d['rows'][0]['pass']=1
        with self.assertRaises(ValueError):Z.analyse(d)
    def test_bad_seed_fails(self):
        d=fixture();d['seed']=24
        with self.assertRaises(ValueError):Z.analyse(d)
    def test_source_hash_binding_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'source.json';out=root/'result.json'
            raw=json.dumps(fixture()).encode();src.write_bytes(raw)
            sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            with self.assertRaisesRegex(ValueError,'mismatch'):
                Z.run(src,out,'0'*40)
            self.assertFalse(out.exists())
            self.assertEqual(Z.run(src,out,sha)['n'],60)
            with self.assertRaises(FileExistsError):Z.run(src,out,sha)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'source.json';out=root/'result.json'
            raw=b'{"kind":"V13_Z6A_EFFORT_BENCH","seed":23,"seed":23,"rows":[]}'
            src.write_bytes(raw)
            sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            with self.assertRaisesRegex(ValueError,'duplicate'):
                Z.run(src,out,sha)

    def test_sign_test(self):
        self.assertEqual(Z._sign_p(3,1),.625)
        self.assertEqual(Z._sign_p(0,0),1.0)

if __name__=='__main__':unittest.main()
