"""Cheap output display boundaries, without a semantic correctness claim."""
import unittest
from v13.common import safe_text,visible_text

class DisplayGuard(unittest.TestCase):
    def test_terminal_and_unicode_overrides_removed_legitimate_languages_preserved(self):
        text='Grüße العربية русский 👩\u200d💻\n\t'
        self.assertEqual(safe_text(text),text)
        bad='\x1b\x00\x7f\x85\ud800\u202e\u2066'
        self.assertEqual(safe_text(bad),'')
        self.assertEqual(safe_text('abc\u202edef'),'abcdef')
        self.assertTrue(visible_text(text))

    def test_invisible_only_is_not_a_visible_answer(self):
        self.assertFalse(visible_text('\n\t\u200b\u200d'))
        self.assertTrue(visible_text('{}'))
        self.assertTrue(visible_text('你好'))

if __name__=='__main__':unittest.main()
