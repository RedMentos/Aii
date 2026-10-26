import tempfile,unittest
from pathlib import Path
from v13 import userrules as U, userrules_second as S
from v13.store import Store as _Store

def Store(d,days):
    h=Path(d);(h/'data/db').mkdir(parents=True,exist_ok=True);return _Store(h,days)

PROBES={'web':{'actions':{'TOOL','NETWORK'},'objects':{'INTERNET','TOOLS'}},'delete_photo':{'actions':{'TOOL','DELETE'},'objects':{'PHOTO','FILE','TOOLS'}},
        'calc':{'actions':{'TOOL','COMPUTE'},'objects':{'CALCULATOR','TOOLS'}}}
LINES=('Lösch niemals meine Fotos.','Mails nur nach Rücksprache mit mir.','Das Internet ist heute langsam.','Du darfst wieder ins Internet.',
       'Mein Kollege meint, du solltest nicht ins Internet.','Die Aufnahmen bleiben, wie sie sind.')
VERDICTS=[None,{'art':'KEINE','betrifft':[]},{'art':'LOCKERUNG','betrifft':['alles']},{'art':'VERBOT','betrifft':['internet']},
          {'art':'ERST_FRAGEN','betrifft':[]},{'art':'UNKLAR','betrifft':['loeschen','rechnen']},{'art':'kaputt'},'unsinn']

def verdicts(clauses):
    rs=[dict(c,id='R'+str(i),status='OPEN' if c['kind']=='UNCLEAR' else 'ACTIVE') for i,c in enumerate(clauses) if c['kind'] in ('FORBID','ASK_FIRST','UNCLEAR')]
    return {p:U.verdict(rs,d)[0] for p,d in PROBES.items()}

class SecondReader(unittest.TestCase):
    def test_S4_never_weaker_than_the_fixed_reader_whatever_the_model_says(self):
        rank={'ALLOW':0,'ASK':1,'DENY':2}
        for line in LINES:
            fixed=U.parse(line);base=verdicts(fixed)
            for v in VERDICTS:
                got=S.combine(fixed,v,line);self.assertEqual(got[:len(fixed)],fixed)  # fixed clauses untouched
                self.assertLessEqual(len(got)-len(fixed),1)
                for p,b in verdicts(got).items():self.assertGreaterEqual(rank[b],rank[base[p]],(line,v,p))
    def test_S2_model_adds_an_open_question_never_a_prohibition(self):
        got=S.combine([],{'art':'VERBOT','betrifft':['internet']},'Das WLAN ist Sperrgebiet.')
        self.assertEqual([(c['kind'],c['reasons'],c['actions']) for c in got],[('UNCLEAR',['SECOND_READER'],['NETWORK'])])
        self.assertEqual(verdicts(got)['web'],'ASK');self.assertEqual(verdicts(got)['calc'],'ALLOW')
        self.assertEqual(S.combine([],{'art':'UNKLAR','betrifft':[]},'x')[0]['actions'],['ANY'])  # no area named: everything
    def test_S3_no_answer_none_or_loosening_change_nothing(self):
        for v in (None,{'art':'KEINE','betrifft':[]},{'art':'LOCKERUNG','betrifft':['internet']},{'art':'VERBOT','betrifft':['web']},{'x':1}):
            self.assertEqual(S.combine([],v,'Hallo'),[])
    def test_covered_area_adds_nothing(self):
        fixed=U.parse('Lösch niemals meine Fotos.');self.assertEqual(S.combine(fixed,{'art':'VERBOT','betrifft':['loeschen']},'x'),fixed)
    def test_modes_shadow_logs_only_active_adds_question(self):
        with tempfile.TemporaryDirectory() as d:
            st=Store(d,30);ask=lambda t:{'art':'VERBOT','betrifft':['internet']}
            self.assertEqual(S.observe(st,'Das WLAN ist für dich zu, okay?','shadow',ask),U.observe(Store(d+'/b',30),'Das WLAN ist für dich zu, okay?'))
            n=len(U.rules(st));out=S.observe(st,'Surfen gehört heute mir allein.','active',ask)  # the fixed reader finds no rule here
            self.assertTrue(any('zweiter Leser' in x for x in out));self.assertEqual(len(U.rules(st)),n+1)
            self.assertEqual(U.rules(st)[-1]['status'],'OPEN')
            st2=Store(d+'/c',30);self.assertEqual(S.observe(st2,'Hallo du.','active',lambda t:None),[])  # model down: fixed reader only
            self.assertEqual(S.observe(st2,'Hallo du.','off',ask),[])

if __name__=='__main__':unittest.main()
