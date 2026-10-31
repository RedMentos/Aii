"""Run117AK independent raw packet/SourceRef/ZIP tamper tests (model-free)."""
from hashlib import sha256
from io import BytesIO
import json
import unittest
import warnings
import zipfile

from tests import test_run117ah_body_source_id_candidate as ah
from scripts import run117ak_independent_body_native_audit as audit


def raw_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


def fixture_item():
    row = ah.rows()[0]
    source = row['prior']
    ref = {'source_id':'source-prior', 'sha256':sha256(source.encode()).hexdigest(),
           'char_start':0,'char_end':len(source),'modality':'text'}
    target = row['policy_span']
    a = source.index(target)
    span = {'text':target,
            'source_ref':dict(ref, char_start=a, char_end=a+len(target)),
            'origin':'STORE_EXACT_USER_NOT_MODEL_QUOTE'}
    archive = 'Archive memo'
    b = source.index(archive)
    end = source.index('draft was withdrawn.',b)+len('draft was withdrawn.')
    distractor = {'text':source[b:end],
                  'source_ref':dict(ref,char_start=b,char_end=end),
                  'origin':'STORE_EXACT_USER_NOT_MODEL_QUOTE'}
    candidates = [{'span_id':'s1',**span},
                  {'span_id':'s2',**distractor}]
    raw = '{"span_id":"s1"}'
    packet = {
        'schema_version':'1.0','packet_id':'packet1','event_id':'event1',
        'provenance':[ref], 'role':'B2_GIST','source_ref':ref,
        'candidates':candidates,'selected_id':'s1',
        'selected_span':span,'model_hypothesis_not_fact':True,
        'source_semantic_truth_authority':False,'output_committed':False,
        'delivery_authority':0,'learning_authority':0,
        'raw_output_sha256':sha256(raw.encode()).hexdigest(),
        'raw_output_bytes':len(raw.encode()),
        'selection_correct_shadow':True,
    }
    payload = raw_json(packet)
    item = {
        'role':'B2_GIST','status':'RECORDED','source_ref':ref,
        'native_final':True,'process_reaped':True,
        'native_metrics':{'status':'FINAL',
                          'actual_model':audit.MODELS['B2_GIST'],
                          'role':'B2_GIST'},
        'packet_id':'packet1',
        'packet_evidence':{'kind':'BodySourceIdSelection',
                           'raw':payload,'sha256':sha256(payload.encode()).hexdigest()},
        'raw_output':raw,'model_id_correct':True,
        'component_status':'SHADOW_SOURCE_ID_SELECTED',
    }
    return row, ref, packet, item


def update_packet(item, packet):
    payload = raw_json(packet)
    item['packet_evidence'] = {
        'kind':'BodySourceIdSelection','raw':payload,
        'sha256':sha256(payload.encode()).hexdigest(),
    }


class NativeAuditTests(unittest.TestCase):
    def test_exact_fixture_selection_recomputed(self):
        row, ref, packet, item = fixture_item()
        self.assertEqual(audit._selection(
            item,'B2_GIST',row['prior'],ref,row['policy_span']),1)
        audit._full_ref(ref,row['prior'])

    def test_forged_candidate_span_rejected_even_if_rehashed(self):
        row, ref, packet, item = fixture_item()
        packet['candidates'][0]['text'] = 'FORGED'
        update_packet(item,packet)
        with self.assertRaisesRegex(ValueError,'SPAN_SOURCE_BINDING_RED'):
            audit._selection(item,'B2_GIST',row['prior'],ref,row['policy_span'])

    def test_wrong_source_ref_rejected_even_if_packet_rehashed(self):
        row, ref, packet, item = fixture_item()
        packet['source_ref'] = dict(ref, sha256='0'*64)
        update_packet(item,packet)
        with self.assertRaisesRegex(ValueError,'SELECTION_PACKET_AUTHORITY_RED'):
            audit._selection(item,'B2_GIST',row['prior'],ref,row['policy_span'])

    def test_model_score_forgery_rejected(self):
        row, ref, packet, item = fixture_item()
        packet['selection_correct_shadow'] = False
        update_packet(item,packet)
        with self.assertRaisesRegex(ValueError,'SELECTION_REPORTED_SCORE_RED'):
            audit._selection(item,'B2_GIST',row['prior'],ref,row['policy_span'])

    def test_raw_output_hash_forgery_rejected(self):
        row, ref, packet, item = fixture_item()
        item['raw_output'] = '{"span_id":"s2"}'
        with self.assertRaisesRegex(ValueError,'SELECTION_OUTPUT_SHA_RED'):
            audit._selection(item,'B2_GIST',row['prior'],ref,row['policy_span'])

    def test_learning_authority_forgery_rejected(self):
        row, ref, packet, item = fixture_item()
        packet['learning_authority'] = 1
        update_packet(item,packet)
        with self.assertRaisesRegex(ValueError,'SELECTION_PACKET_AUTHORITY_RED'):
            audit._selection(item,'B2_GIST',row['prior'],ref,row['policy_span'])

    def test_full_source_wrong_sha_and_offsets(self):
        row, ref, packet, item = fixture_item()
        for forged in (dict(ref,sha256='0'*64),
                       dict(ref,char_end=len(row['prior'])-1)):
            with self.subTest(forged=forged):
                with self.assertRaisesRegex(ValueError,'FULL_SOURCE_REF_RED'):
                    audit._full_ref(forged,row['prior'])

    def test_duplicate_and_nonfinite_json_rejected(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}'):
            with self.assertRaises(ValueError):
                audit._json(raw)

    def test_outer_zip_checksum_coverage_rejected(self):
        b = BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            z.writestr('x','abc')
            z.writestr('SHA256SUMS','')
        with zipfile.ZipFile(BytesIO(b.getvalue())) as z:
            with self.assertRaisesRegex(ValueError,'OUTER_SUM_COVERAGE_RED'):
                audit._sums(z)

    def test_outer_duplicate_zip_entries_rejected(self):
        b = BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(b,'w') as z:
                z.writestr('x','a')
                z.writestr('x','b')
                z.writestr('SHA256SUMS','')
        with zipfile.ZipFile(BytesIO(b.getvalue())) as z:
            with self.assertRaisesRegex(ValueError,'OUTER_DUPLICATE_ENTRY_RED'):
                audit._sums(z)

    def test_original_zip_sha_must_match_before_read(self):
        with self.assertRaisesRegex(ValueError,'ORIGINAL_ARTIFACT_SHA_RED'):
            audit.audit(b'not an artifact',expected_sha='0'*64)


if __name__=='__main__':
    unittest.main()
