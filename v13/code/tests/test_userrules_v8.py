"""WP-UR8 (2026-10-22): v8 of the fixed rule reader and the caution-only second opinion (v13/userrules_second.py).
K8 of docs/proofs/continuation-20261022/user-rules-v8/PREREG.md: the second opinion never changes, loosens or removes a rule."""
import unittest
from v13 import userrules as U
from v13 import userrules_second as S

SAMPLES=('Lösch niemals meine Notizen.','Frag mich vorher, bevor du etwas installierst.','Du kannst wieder Mails verschicken.',
         'Das funktioniert nicht.','Kein Internet!','Maybe don\'t send that email yet.','Speicher die Notiz bitte ab.',
         'Das WLAN ist für dich ab jetzt Sperrgebiet.','Ich bin dagegen, dass du Module installierst.','Hallo, wie geht es dir?')

class V8(unittest.TestCase):
    def test_block_word_without_target_asks_about_everything(self):
        rs=U.parse('Das WLAN ist für dich ab jetzt Sperrgebiet.',second='off')
        self.assertTrue(any(r['reasons']==['BLOCK'] and r['objects']==['ALL'] and 'ANY' in r['actions'] for r in rs))
        rs=U.parse('Fotos sind tabu.',second='off')  # target known: no extra question
        self.assertFalse(any('BLOCK' in r['reasons'] for r in rs))
    def test_kaputt_is_no_statement_any_more(self):
        self.assertEqual([r['kind'] for r in U.parse('Mach meine alten Notizen bloß nicht kaputt.',second='off')],['FORBID'])

class SecondOpinion(unittest.TestCase):
    def test_only_adds_an_open_question(self):
        for t in SAMPLES:
            for s in ('jef',lambda x:True,lambda x:False):
                base=U.parse(t,second='off');got=U.parse(t,second=s)
                self.assertEqual(got[:len(base)],base,t)  # every rule of the fixed reader unchanged and first
                for extra in got[len(base):]:
                    self.assertEqual((extra['kind'],extra['reasons'],extra['objects']),('UNCLEAR',['SECOND'],['ALL']),t)
    def test_never_asked_when_the_fixed_reader_found_a_restriction(self):
        calls=[]
        U.parse('Lösch niemals meine Notizen.',second=lambda x:calls.append(x) or True)
        self.assertEqual(calls,[])
    def test_always_yes_turns_every_unruled_line_into_a_question_never_a_rule(self):
        for t in SAMPLES:
            kinds={r['kind'] for r in U.parse(t,second=lambda x:True)}
            self.assertTrue(kinds&{'FORBID','ASK_FIRST','UNCLEAR'},t)
            self.assertNotIn('LOOSEN',kinds-{r['kind'] for r in U.parse(t,second='off')},t)
    def test_broken_second_opinion_asks(self):
        def boom(x):raise RuntimeError('x')
        self.assertTrue(any('SECOND' in r['reasons'] for r in U.parse('Hallo, wie geht es dir?',second=boom)))
    def test_learned_reader_is_deterministic_and_plain_python(self):
        m=S.load();self.assertEqual(m['schema'],'USER_RULES_SECOND_V1')
        self.assertTrue(0<m['threshold']<1)
        self.assertEqual(S.score('Kein Internet mehr für dich.'),S.score('Kein Internet mehr für dich.'))
        self.assertTrue(S.suspects('Du lässt die Finger von meinen Aufnahmen.'))  # known round-7 miss of the fixed reader
    def test_loosening_in_chat_still_never_loosens(self):
        self.assertFalse(any(r['kind']=='LOOSEN' and 'SECOND' in r['reasons'] for t in SAMPLES for r in U.parse(t,second='jef')))

if __name__=='__main__':unittest.main()
