"""C2 typed-native boundary: source metadata cannot become executive authority."""
import unittest
from v13.fastpolicy import _native

class C2NativeContract(unittest.TestCase):
    def test_flat_untyped_metadata_rejected(self):
        self.assertEqual(_native({'tool':'danger','memory_key':'secret','answer_type':'number'}), {})
        self.assertEqual(_native({'schema':'Other/1','executive':{'tool':'danger'}}), {})
        self.assertEqual(_native({'schema':'C2ExecutiveFields/1','tool':'danger'}), {})
        self.assertEqual(_native({'schema':'C2ExecutiveFields/1','executive':'bad','tool':'danger'}), {})

    def test_typed_fields_only(self):
        x={'schema':'C2ExecutiveFields/1',
           'executive':{'answer_type':'number','memory_key':'  source  ','tool':' calculator '},
           'tool':'forged','memory_key':'forged'}
        self.assertEqual(_native(x),{'answer_type':'number','memory_key':'source','tool':'calculator'})

    def test_nested_untrusted_observation_ignored(self):
        x={'schema':'C2ExecutiveFields/1','executive':{'observation':{'tool':'forged'},'answer_type':'free'}}
        self.assertEqual(_native(x),{'answer_type':'free'})
        self.assertEqual(_native(None),{})

if __name__=='__main__':
    unittest.main()
