import unittest
from v13.percept_integrity import validate_a1_tiling

class A1Tiling(unittest.TestCase):
    def test_lossless_two_segments(self):
        s="Hello.  World\n"
        seg=[{"text":s[:7],"source_ref":{"char_start":0,"char_end":7}},
             {"text":s[7:],"source_ref":{"char_start":7,"char_end":len(s)}}]
        p=validate_a1_tiling(s,seg)
        self.assertEqual((p["status"],p["source_chars"],p["segments"]),("SOURCE_EXACT",len(s),2))
    def test_empty(self):
        self.assertEqual(validate_a1_tiling("",[])["segments"],0)
    def test_gap(self):
        with self.assertRaisesRegex(ValueError,"INTERVAL"):
            validate_a1_tiling("abc",[{"text":"bc","source_ref":{"char_start":1,"char_end":3}}])
    def test_overlap(self):
        with self.assertRaisesRegex(ValueError,"INTERVAL"):
            validate_a1_tiling("abc",[{"text":"ab","source_ref":{"char_start":0,"char_end":2}},
                                      {"text":"bc","source_ref":{"char_start":1,"char_end":3}}])
    def test_corrupt_text(self):
        with self.assertRaisesRegex(ValueError,"MISMATCH"):
            validate_a1_tiling("abc",[{"text":"xyz","source_ref":{"char_start":0,"char_end":3}}])
    def test_missing_tail(self):
        with self.assertRaisesRegex(ValueError,"FULLY_TILED"):
            validate_a1_tiling("abc",[{"text":"ab","source_ref":{"char_start":0,"char_end":2}}])
    def test_boolean_offset(self):
        with self.assertRaisesRegex(ValueError,"INTERVAL"):
            validate_a1_tiling("abc",[{"text":"abc","source_ref":{"char_start":False,"char_end":3}}])
    def test_unicode(self):
        s="🎤 ä 音"
        self.assertEqual(validate_a1_tiling(s,[{"text":s,"source_ref":{"char_start":0,"char_end":len(s)}}])["source_chars"],len(s))

if __name__=="__main__":unittest.main()
