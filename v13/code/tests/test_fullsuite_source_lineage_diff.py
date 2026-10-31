"""Adversarial byte/line/source-set controls for exact lineage diff."""
import hashlib
import unittest
from scripts.fullsuite_source_lineage_diff import compare,digest


class ExactDiff(unittest.TestCase):
    def test_exact_same_bytes(self):
        d=compare({'a':'a\nb\n'},{'a':'a\nb\n'})['a']
        self.assertTrue(d['byte_equal']);self.assertEqual(d['changed_hunks'],0)
        self.assertIsNone(d['first_live_line'])

    def test_change_pin_and_first_line(self):
        d=compare({'a':'a\nc\n'},{'a':'a\nb\n'})['a']
        self.assertFalse(d['byte_equal']);self.assertEqual(d['changed_hunks'],1)
        self.assertEqual(d['first_expected_line'],2);self.assertEqual(d['first_live_line'],2)

    def test_eof_newline_drift(self):
        d=compare({'a':'a\nb'},{'a':'a\nb\n'})['a']
        self.assertFalse(d['byte_equal']);self.assertEqual(d['changed_hunks'],1)

    def test_addition_before_first_line(self):
        d=compare({'a':'NEW\na\n'},{'a':'a\n'})['a']
        self.assertEqual(d['first_expected_line'],1);self.assertEqual(d['first_live_line'],1)

    def test_file_set_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'FILE_SET'):
            compare({'a':'x'},{'b':'x'})

    def test_type_refusal(self):
        with self.assertRaisesRegex(TypeError,'NOT_TEXT'):
            compare({'a':b'raw'},{'a':'raw'})

    def test_no_mutation(self):
        actual={'a':'live\n'}; expected={'a':'frozen\n'}
        original=(dict(actual),dict(expected))
        compare(actual,expected)
        self.assertEqual((actual,expected),original)

    def test_digest_utf8_exact(self):
        self.assertEqual(digest('ä\n'),hashlib.sha256('ä\n'.encode()).hexdigest())


if __name__=='__main__':unittest.main()
