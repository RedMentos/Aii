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

    def test_baseline_offer_native_final_is_metrics_not_missing_key(self):
        row, ref, _, _ = fixture_item()
        offer = {'schema_version':'1.0','packet_id':'offer1',
                 'event_id':'event1','provenance':[ref],
                 'role':'B2_GIST'}
        query = {'schema_version':'1.0','packet_id':'query1',
                 'event_id':'event1','provenance':[ref],
                 'target_role':'B2_GIST'}
        def evidence(kind, packet):
            raw = raw_json(packet)
            return {'kind':kind,'raw':raw,
                    'sha256':sha256(raw.encode()).hexdigest()}
        item = {'role':'B2_GIST','phase':'prior','status':'RECORDED',
                'source_ref':ref,'process_reaped':True,
                'native_metrics':{'status':'FINAL',
                    'actual_model':audit.MODELS['B2_GIST'],
                    'role':'B2_GIST'},
                'packet_id':'offer1','query_packet_id':'query1',
                'packet_evidence':evidence('OfferPacket',offer),
                'query_evidence':evidence('QueryPacket',query)}
        # Original Run117AH _observe does not emit native_final on offers.
        audit._offer(item,'B2_GIST',ref)
        query['provenance'] = []
        item['query_evidence'] = evidence('QueryPacket',query)
        with self.assertRaisesRegex(ValueError,'OFFER_QUERY_PROVENANCE_RED'):
            audit._offer(item,'B2_GIST',ref)

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

    def test_missing_original_native_report_preserves_real_red(self):
        def make_zip(stage_red):
            exits = {stage:(1 if stage == 'SOURCE' and stage_red else 0)
                     for stage in audit.STAGES}
            result = {'head':audit.HEAD,'seed':1069,
                      'fixture_sha256':audit.FIXTURE_SHA,
                      'exits':exits,'step2_promoted':False,
                      'b3_promoted':False,'jepa_weight':0,
                      'redmi_measured':False,'whole_system_complete':False}
            entries = {'HEAD.txt':audit.HEAD,
                       'RESULT.json':raw_json(result)}
            entries.update({stage+'_EXIT.txt':str(code)
                            for stage,code in exits.items()})
            sums = ''.join(sha256(data.encode()).hexdigest()+
                           '  ./'+name+'\\n'
                           for name,data in sorted(entries.items()))
            entries['SHA256SUMS'] = sums
            b = BytesIO()
            with zipfile.ZipFile(b,'w') as z:
                for name,data in entries.items():
                    z.writestr(name,data)
            return b.getvalue()
        original_red = make_zip(True)
        result = audit.audit(original_red,
                             expected_sha=sha256(original_red).hexdigest())
        self.assertEqual(result['status'],
                         'INDEPENDENT_ORIGINAL_NATIVE_NOT_RUN_RED_PRESERVED')
        self.assertEqual(result['original_exits']['SOURCE'],1)
        forged_green = make_zip(False)
        with self.assertRaisesRegex(ValueError,
                                    'GREEN_RECEIPT_MISSING_ORIGINAL_ARTIFACT_RED'):
            audit.audit(forged_green,
                        expected_sha=sha256(forged_green).hexdigest())

    def test_original_zip_sha_must_match_before_read(self):
        with self.assertRaisesRegex(ValueError,'ORIGINAL_ARTIFACT_SHA_RED'):
            audit.audit(b'not an artifact',expected_sha='0'*64)


if __name__=='__main__':
    unittest.main()
