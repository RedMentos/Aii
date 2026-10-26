"""Run559 source-only adversarial offline verifier tests; no model/native."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import run559_offline_review as review
import run500_step2_stage_map as stages
import run504_remaining980_schedule as schedule


class OfflineFutureBatchReview(unittest.TestCase):
    def test_original_frozen_future_batch_coverage_and_mixed_seeds(self):
        full=stages.registration();future=schedule.registration()
        self.assertEqual(len(future['batches']),24)
        self.assertEqual(sum(x['expected_rows'] for x in future['batches']),980)
        self.assertEqual(future['batches'][1]['stage_ids'],
                         ['A_s31_p03','A_s31_p04','A_s32_p00'])
        self.assertEqual([(s['arm'],s['seed']) for s in
                          [stages.choose(full,sid) for sid in future['batches'][1]['stage_ids']]],
                         [('A',31),('A',31),('A',32)])
        self.assertEqual(future['batches'][-1]['expected_rows'],14)

    def test_oracle_twelve_fields_exact_and_type_strict(self):
        oracle={'project':'Project Vesper','action':'A','options':[
            {'entity':'A','cost':8,'remaining':4,'days':2,'local':True,'eligible':True},
            {'entity':'B','cost':10,'remaining':2,'days':3,'local':False,'eligible':False}]}
        answer=json.loads(json.dumps(oracle))
        self.assertEqual(sum(review.independent_score(answer,oracle).values()),12)
        answer['options'][0]['cost']=8.0
        checks=review.independent_score(answer,oracle)
        self.assertFalse(checks['A.cost'])
        self.assertEqual(sum(checks.values()),11)
        answer['options'][0]['cost']=8
        answer['options'][0]['eligible']='true'
        self.assertFalse(review.independent_score(answer,oracle)['A.eligible'])
        for bad in ({}, {'project':'Project Vesper','action':'A','options':[]},
                    {'project':'Project Vesper','action':'A','options':[answer['options'][0]]*2}):
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,'MALFORMED'):
                review.independent_score(bad,oracle)

    def test_manifest_rejects_modified_member_missing_member_and_duplicate(self):
        def archive(data,entries):
            out=io.BytesIO()
            with zipfile.ZipFile(out,'w') as z:
                for name,value in data:z.writestr(name,value)
                z.writestr('SHA256SUMS.txt',''.join(
                    hashlib.sha256(value).hexdigest()+'  '+name+'\n' for name,value in entries))
            out.seek(0)
            return out
        good=[('first.json',b'{}'),('second.json',b'[]')]
        with zipfile.ZipFile(archive(good,good)) as z:
            self.assertEqual(review.manifest(z,'SHA256SUMS.txt'),2)
        tampered=[('first.json',b'{"changed":1}'),('second.json',b'[]')]
        with zipfile.ZipFile(archive(tampered,good)) as z:
            with self.assertRaisesRegex(ValueError,'RAW_SHA_MISMATCH'):
                review.manifest(z,'SHA256SUMS.txt')
        with zipfile.ZipFile(archive(good,good[:1])) as z:
            with self.assertRaisesRegex(ValueError,'RAW_MANIFEST_INCOMPLETE'):
                review.manifest(z,'SHA256SUMS.txt')
        with zipfile.ZipFile(archive(good+[good[0]],good)) as z:
            with self.assertRaisesRegex(ValueError,'DUPLICATE_ZIP_MEMBER'):
                review.manifest(z,'SHA256SUMS.txt')

    def test_unknown_batch_prefix_and_bad_zip_hash_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw=Path(tmp)/'raw.zip';safe=Path(tmp)/'safe.zip'
            raw.write_bytes(b'not zip');safe.write_bytes(b'not zip')
            sha=hashlib.sha256(b'not zip').hexdigest()
            for bid in ('FUTURE_000','FUTURE_025','FUTURE_001_BAD'):
                with self.subTest(batch=bid),self.assertRaisesRegex(ValueError,'UNKNOWN_FUTURE_BATCH'):
                    review.audit(raw,safe,sha,sha,'h','RUN507',bid)
            with self.assertRaisesRegex(ValueError,'INVALID_RUN_PREFIX'):
                review.audit(raw,safe,sha,sha,'h','../../../etc','FUTURE_001')
            with self.assertRaisesRegex(ValueError,'PINNED_ZIP_SHA_MISMATCH'):
                review.audit(raw,safe,'0'*64,sha,'h','RUN507','FUTURE_001')

    def test_manifest_rejects_unsafe_member_path(self):
        data=[('../escape',b'{}')]
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            z.writestr('../escape',b'{}')
            z.writestr('SHA256SUMS.txt',hashlib.sha256(b'{}').hexdigest()+'  ../escape\n')
        out.seek(0)
        with zipfile.ZipFile(out) as z:
            with self.assertRaisesRegex(ValueError,'UNSAFE_ZIP_MEMBER'):
                review.manifest(z,'SHA256SUMS.txt')


if __name__=='__main__':unittest.main()
