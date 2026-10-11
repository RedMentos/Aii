import unittest
from v13.store import telemetry_metrics


class NativeTelemetryPrivacy(unittest.TestCase):
    def test_decoder_categories_and_resource_measurements_survive_without_content(self):
        measured={'component':'output_adapter','prediction':{'first_token_bias':[[123,1.5]],'nearest_native_cosine':.97,'reference_text':'Private target'},'held_out_per_native_token':{'123':{'before':{'loss':.2},'after':{'loss':.3},'pass':False},'Private word':{'pass':True},'65536':{'pass':True}},'native_pressure':{'resource_cancel_signalled':False,'critical_reason':'MEMORY_CRITICAL','native_kv_bytes':None,'snapshot':{'mem_available_bytes':1000,'battery_temperature_c':None}}}
        result=telemetry_metrics(measured)
        self.assertEqual(result['component'],'output_adapter')
        self.assertEqual(result['prediction'],{'first_token_bias':[[123,1.5]],'nearest_native_cosine':.97})
        self.assertEqual(result['held_out_per_native_token'],[{'token_id':123,'before':{'loss':.2},'after':{'loss':.3},'pass':False}])
        self.assertEqual(result['native_pressure'],measured['native_pressure'])


if __name__=='__main__':unittest.main()
