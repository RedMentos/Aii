import copy
import unittest
from v13.model_footprint_candidate import audit

class FootprintAudit(unittest.TestCase):
    def setUp(self):
        self.spec={'models':{'body':{'model_id':'x','main_file':'a.gguf','files':[
            {'local_name':'a.gguf','sha256':'a'*64,'size':1048576}]}}}
        self.profiles={'entries':{'a'*64:{'size_bytes':1048576,'size_mib':2.0,
                                        'evidence':'CLOUD_X86_LOWER_BOUND'}}}
    def row(self, profiles=None):
        return audit(self.spec,self.profiles if profiles is None else profiles,('body',))['rows'][0]
    def test_profile_not_device_proof(self):
        self.assertEqual(self.row()['status'],'PROFILE_CLOUD_X86_LOWER_BOUND')
        self.assertFalse(self.row()['redmi_proof'])
    def test_forged_device_claim_not_authorized(self):
        p=copy.deepcopy(self.profiles);p['entries']['a'*64]['evidence']='DEVICE_MEASURED'
        self.assertFalse(self.row(p)['redmi_proof'])
        self.assertFalse(audit(self.spec,p,('body',))['runtime_admission_authorized'])
    def test_profile_size_mismatch_rejected(self):
        p=copy.deepcopy(self.profiles);p['entries']['a'*64]['size_bytes']=123
        self.assertEqual(self.row(p)['status'],'PROFILE_REJECTED')
    def test_invalid_nan_rejected(self):
        p=copy.deepcopy(self.profiles);p['entries']['a'*64]['size_mib']=float('nan')
        self.assertEqual(self.row(p)['status'],'PROFILE_REJECTED')
    def test_missing_profile_not_estimated_from_file(self):
        row=self.row({'entries':{}})
        self.assertIsNone(row['resident_mib'])
        self.assertEqual(row['file_mib'],1.0)
    def test_duplicate_main_file_rejected(self):
        self.spec['models']['body']['files']*=2
        self.assertEqual(self.row()['status'],'INVALID_MAIN_FILE')
    def test_missing_role_explicit(self):
        self.assertEqual(audit(self.spec,self.profiles,('needle',))['rows'][0]['status'],'MISSING_SPEC')
    def test_bad_sha_rejected(self):
        self.spec['models']['body']['files'][0]['sha256']='wrong'
        self.assertEqual(self.row()['status'],'INVALID_FILE_METADATA')

if __name__=='__main__': unittest.main()
