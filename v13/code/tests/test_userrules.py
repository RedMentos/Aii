"""2026-10-21 user rules: prohibitions and "ask me first" from the user's own words, read by a fixed component (no model),
enforced in the tool policy (IH-H29), shown with fixed notices. One test per guarantee G1-G6 of v13/userrules.py."""
import json,tempfile,unittest
from pathlib import Path
from v13.runtime import Runtime
from v13 import userrules as U
from v13 import toolstep as T
from v13.agi import hub
from v13.broker import preview_text,rule_notice_text
from v13.operator import Operator

def kinds(text):return [c['kind'] for c in U.parse(text)]

class Parse(unittest.TestCase):
    def test_forbid_and_ask_in_both_languages(self):
        for text,kind in (('Never delete my notes.','FORBID'),('Lösch niemals meine Notizen.','FORBID'),('Du darfst meine Fotos nicht löschen.','FORBID'),
                          ("Don't send emails without asking me.",'ASK_FIRST'),('Frag mich vorher, bevor du etwas installierst.','ASK_FIRST'),
                          ('Installier nichts ohne meine Erlaubnis.','ASK_FIRST'),('Finger weg von meinen Notizen!','FORBID'),('Kein Internet!','FORBID')):
            self.assertEqual(kinds(text),[kind],text)
    def test_positive_negations_and_statements_are_not_rules(self):
        for text in ("Don't forget to save my notes.",'Vergiss nicht, die Notiz zu speichern.',"Don't worry about it.",'Keine Sorge.',
                     "I don't know.",'Das funktioniert nicht.','No thanks.','Never mind.','Please save this as a note.','Can you delete the old note?',
                     "I didn't delete anything yesterday."):
            self.assertEqual(kinds(text),[],text)
    def test_unclear_sentences_become_questions(self):
        for text in ('Maybe don\'t send that email yet.','Mein Chef meint, du darfst keine Mails verschicken.',"Why don't you save it?",
                     "Don't do that again.",'I never delete my notes.'):
            self.assertEqual(kinds(text),['UNCLEAR'],text)
    def test_v2_unknown_wording_of_a_possible_rule_is_asked_not_ignored(self):
        # v1 read these model rewrites as "no rule" (docs/proofs/continuation-20261021/user-rules/BEFUND.md)
        for text in ('Please refrain from employing any instruments today.','Halt die Verwendung des Taschenrechners.',
                     'You are strictly prohibited from engaging with any digital platforms.','Vermeide es, meine Rezepte zu löschen.'):
            self.assertIn(kinds(text)[0] if kinds(text) else 'NONE',('FORBID','UNCLEAR'),text)
        for text in ('Before you proceed with any action, I advise you to speak first.','Erzähl mir, bevor du etwas tust.','Sag mir immer vor, was du tun willst.'):
            self.assertEqual(kinds(text),['ASK_FIRST'],text)
    def test_v3_round2_failure_forms_are_read(self):
        # the 8 sentences v2 missed in round 2 (docs/proofs/continuation-20261021/user-rules/BEFUND.md)
        for text,ok in (('Tell me ahead of time what you intend to do.',('ASK_FIRST',)),('Maintain a safe distance from my pictures.',('FORBID',)),
                        ('I never let you take my recipes away.',('FORBID',)),('It might be better to hold off on that message.',('UNCLEAR',)),
                        ('My sibling advises against accessing the web.',('UNCLEAR',)),('I forbade you from running any programs.',('FORBID',)),
                        ('The indication warned against coming inside.',('UNCLEAR',)),('Gut vor dem Senden, mir zeigen.',('ASK_FIRST',))):
            self.assertIn(kinds(text)[0] if kinds(text) else 'NONE',ok,text)
        self.assertEqual(kinds('I never delete my notes.'),['UNCLEAR'])  # about oneself, the AI is not addressed
        self.assertEqual(U.parse('I forbade you from running any programs.')[0]['actions'],['RUN'])  # "running" -> run
    def test_v4_casual_requests_and_prohibitions_without_negation(self):
        # round-3 failure forms (docs/proofs/continuation-20261022/user-rules-v3/BEFUND.md)
        for text in ('Hey, could you like, not go on the internet, please?','Can you please make sure not to delete any of my notes?',
                     'Just put the calculator away, okay?','Stay offline, or else.','Seriously, let\'s skip the file transfers, okay?',
                     'Keep out of my confidential communications.','Please preserve my notes and refrain from transmitting them to any external destination.'):
            self.assertIn(kinds(text)[0] if kinds(text) else 'NONE',('FORBID','UNCLEAR'),text)
        for text in ("Could you hold up on forwarding messages until I've given the all-clear?","Just a heads-up – let me glance at what you're about to post first, okay?",
                     'Keep your hands off my phone unless I give you the green light.'):
            self.assertIn(kinds(text)[0] if kinds(text) else 'NONE',('ASK_FIRST','UNCLEAR'),text)
        c=U.parse('Keep your hands off my phone unless I give you the green light.')[0];self.assertIn('ALL',c['objects'])
        self.assertIn('ANY',c['actions'])  # "phone" is an object here, the action word widens
        self.assertIn('DELETE',U.parse('Please preserve my notes and refrain from transmitting them.')[0]['actions'])
        for text in ('Can you delete the old note?',"Don't forget to save my notes.",'Don\'t worry about the budget.','No thanks.'):
            self.assertEqual(kinds(text),[],text)
        self.assertEqual(kinds('You can install whatever you need, no worries.'),['LOOSEN'])
    def test_v5_condition_is_never_a_loosening_and_german_hold_forms(self):
        # round-4 failure forms (docs/proofs/continuation-20261022/user-rules-v4/BEFUND.md)
        for text in ('Du darfst nur Nachrichten senden, wenn du meine Genehmigung hast.','Du darfst erst Nachrichten versenden, wenn ich dir das erlaube.',
                     'Kein Kram ohne mein grünes Licht.'):
            self.assertIn(kinds(text)[0] if kinds(text) else 'NONE',('ASK_FIRST','UNCLEAR'),text)
        for text in ('Bleib ab von meinen Notizen!','Kein Versand!','Verzichte auf Werkzeuge.','Meine Notizen in Ruhe lassen.','Schütze meine Notizen.'):
            self.assertIn(kinds(text)[0] if kinds(text) else 'NONE',('FORBID','UNCLEAR'),text)
        self.assertIn('INTERNET',U.parse('Bitte keine Dateien herunterladen.')[0]['objects'])  # downloading is about the internet too
        self.assertEqual(kinds('Du darfst jetzt wieder ins Internet.'),['LOOSEN'])
    def test_v6_broad_net_turns_missed_rule_sentences_into_open_questions(self):
        # holdout_de2 / round-5 failure forms (docs/proofs/continuation-20261022/user-rules-v5/BEFUND.md)
        for text in ('Fass mein Handy nicht an.','Gib meine Telefonnummer an niemanden weiter.','Schluss mit dem Internet.',
                     'Von meinen Dateien lässt du die Finger.','Erst fragen, dann ändern – das gilt für meine Dateien.',
                     'Präsentiere mir jeden Entwurf, bevor er abgeschickt wird.','Ich bitte um Nichtveränderung meiner Notizen.'):
            self.assertTrue(kinds(text) and kinds(text)[0] in ('FORBID','ASK_FIRST','UNCLEAR'),text)
        c=U.parse('Schluss mit dem Internet.')[0];self.assertEqual((c['reasons'],c['suggest']),(['NET'],'FORBID'))
        self.assertIn('NETWORK',c['actions']);self.assertIn('UNKNOWN',c['actions'])  # unknown words widen, never narrow
        self.assertIn('ich verstehe den Satz nicht sicher',U.notice(dict(c,id='R2',status='OPEN')))
        for text in ('Heute habe ich nichts heruntergeladen.','Kein Problem, die Rechnung passt.','Gestern hatte ich keine Zeit für Notizen.',
                     'Vergiss nicht, die Fotos zu sichern.'):
            self.assertEqual(kinds(text),[],text)  # no rule, no question
        self.assertNotIn('SEND',U.parse('Bitte gib mir immer im Voraus mitteilst, was du machen möchtest.')[0]['actions'])  # "mitteilst" is not "teil"
        self.assertIn('SEND',U.parse('Bitte schreibe keine E-Mails in meinem Namen.')[0]['actions'])
    def test_v7_block_words_compounds_device_and_requests(self):
        # holdout_de3 / round-6 failure forms (docs/proofs/continuation-20261022/user-rules-v6/BEFUND.md)
        for text in ('Die Internetverbindung ist zurzeit ausgeschlossen.','Eine Änderung ist ausgeschlossen.','Stelle keine Zusatzprogramme herunter.',
                     'Mein Telefon ist dir blockiert.','Ich möchte nicht, dass du addiert.','Sag mir immer mal, wenn du rechnen willst.',
                     "Gib mir erstmal 'ne Vorschau, wie du die Notiz anpasst, okay?",'Ehrlich gesagt stört mich es, wenn du an meinen Notizen herumfare.',
                     'Ich habe das Internet für dich abgeschaltet.'):
            self.assertTrue(kinds(text) and kinds(text)[0] in ('FORBID','ASK_FIRST','UNCLEAR'),text)
        cs=U.parse('Na klar, erst wenn ich sag, dann machst du was mit dem Installieren.')  # the target sits in the "dann" clause
        self.assertTrue(any('INSTALL' in c['actions'] or 'ANY' in c['actions'] for c in cs))
        c=U.parse('Auf dem Schild steht: Nicht berühren.')[0];self.assertEqual((c['kind'],c['reasons']),('UNCLEAR',['QUOTED']))
        self.assertIn('MODULE',U.parse('Keine Zusatzprogramme.')[0]['objects'])
    def test_v7_reports_about_others_the_past_or_faults_are_no_rules_but_firm_forms_stay(self):
        for text in ('Niemand hat mir gesagt, dass das Modul neu ist.','Du hast nichts falsch gemacht.','Warum geht das Internet nicht?',
                     'Heute geht das Netz wirklich nicht so schnell.','Nun, es war nichts.','Ich habe gestern nichts gelöscht.'):
            self.assertEqual(kinds(text),[],text)
        for text in ('Löschen geht gar nicht.','Nichts ist erlaubt.','Niemand bekommt von dir eine Nachricht.','Das Internet geht dich nichts an.',
                     'Niemand hat dir erlaubt, Fotos zu löschen.','Du hast nie Fotos gelöscht und wirst es auch nie.','Lass alles, wie es ist.'):
            self.assertTrue(kinds(text) and kinds(text)[0] in ('FORBID','ASK_FIRST','UNCLEAR'),text)  # dev_v7 counterexamples
    def test_v6_firm_rule_notice_says_how_to_correct_the_reading(self):
        c=U.parse('Lösch niemals meine Fotos.')[0]
        self.assertIn('Falsch verstanden?',U.notice(dict(c,id='R1',status='ACTIVE')))
    def test_v3_lexicon_is_data_with_evidence_and_refuses_sealed_sentences(self):
        for e in U.LEXICON['entries']:
            self.assertTrue(e['evidence'].strip());self.assertFalse(any(x in e['evidence'] for x in U.LEXICON['sealed']))
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'lex.json';f.write_text(json.dumps({'sealed':['round3'],'entries':[]}))
            with self.assertRaises(ValueError):U.extend({'slot':'FORBID','value':'nope','evidence':''},f)
            with self.assertRaises(ValueError):U.extend({'slot':'FORBID','value':'nope','evidence':'round3: a sealed sentence'},f)
            with self.assertRaises(ValueError):U.extend({'slot':'NOWHERE','value':'x','evidence':'dev'},f)
        U.load_lexicon()
    def test_v3_unclear_rule_carries_a_proposal(self):
        c=U.parse('My sibling advises against accessing the web.')[0];self.assertEqual(c['suggest'],'FORBID')
        text=U.notice(dict(c,id='R4',status='OPEN'));self.assertIn('Mein Vorschlag: als Verbot lesen (:regel verbot R4)',text)
        c=U.parse('Vielleicht vorher fragen, bevor du etwas sendest.')[0];self.assertEqual((c['kind'],c['suggest']),('UNCLEAR','ASK_FIRST'))
    def test_loosening_is_recognised_but_not_a_rule(self):
        self.assertEqual(kinds('You can delete notes again now.'),['LOOSEN']);self.assertEqual(kinds('Du darfst jetzt wieder ins Internet.'),['LOOSEN'])
    def test_every_named_action_and_object_counts(self):
        c=U.parse('Never delete or overwrite my notes, and do not send them anywhere either.')[0]
        self.assertLessEqual({'DELETE','SEND'},set(c['actions']));self.assertIn('NOTE',c['objects'])
        c=U.parse('Lösche und verschicke niemals meine Fotos oder Nachrichten.')[0]
        self.assertLessEqual({'DELETE','SEND'},set(c['actions']));self.assertLessEqual({'PHOTO','MESSAGE'},set(c['objects']))
    def test_clause_after_but_inherits_the_object(self):
        cs=U.parse('Schreib die Notiz, aber lösch niemals die alte.');self.assertEqual([c['kind'] for c in cs],['FORBID'])
        self.assertIn('NOTE',cs[0]['objects'])
        cs=U.parse('Delete the old drafts, but not my photos.');self.assertEqual(cs[0]['actions'],['DELETE']);self.assertEqual(cs[0]['objects'],['PHOTO'])

class Match(unittest.TestCase):
    def v(self,text,action):
        rs=[dict(c,id='R%d'%i,status='OPEN' if c['kind']=='UNCLEAR' else 'ACTIVE') for i,c in enumerate(U.parse(text),1) if c['kind']!='LOOSEN']
        return U.verdict(rs,action)[0]
    REPLACE=U.describe('sandbox_note',{},{'effect':'REPLACE'});CREATE=U.describe('sandbox_note',{},{'effect':'CREATE'})
    CALC={'actions':{'TOOL','COMPUTE'},'objects':{'CALCULATOR','TOOLS'}}
    def test_G3_unknown_words_widen_to_ask(self):
        self.assertEqual(self.v('Never delete my notes.',self.REPLACE),'DENY');self.assertEqual(self.v('Never delete my notes.',self.CREATE),'ALLOW')
        self.assertEqual(self.v('Never delete my recipes.',self.REPLACE),'ASK')  # recipes: unknown word -> ask, never "probably not meant"
        self.assertEqual(self.v('Never delete files, except the drafts.',self.REPLACE),'ASK')
        self.assertEqual(self.v('Stop using the calculator.',self.CALC),'DENY');self.assertEqual(self.v('Never delete my notes.',self.CALC),'ALLOW')
    def test_G4_open_question_asks(self):
        self.assertEqual(self.v('Vielleicht solltest du lieber nichts löschen.',self.REPLACE),'ASK')
    def test_G5_undeclared_tool_is_asked_while_rules_exist(self):
        mystery=U.describe('mystery_tool');self.assertFalse(mystery['declared'])
        self.assertEqual(self.v('Never delete my notes.',mystery),'ASK');self.assertEqual(U.verdict([],mystery)[0],'ALLOW')
    def test_ask_first_never_denies(self):
        self.assertEqual(self.v('Always ask me before you write anything to my files.',self.CREATE),'ASK')
        self.assertEqual(self.v('Tell me before you do anything.',self.CALC),'ASK')

class Live(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.notes=[];self.r.notice=self.notes.append;self.reg=hub(self.r).tools
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_G1_only_the_users_own_lines_create_rules(self):
        with self.assertRaises(ValueError):U.add(self.r.store,'Never delete my notes.','MODEL')
        self.assertEqual(U.rules(self.r.store),[])
        self.assertEqual(len(U.add(self.r.store,'Never delete my notes.','USER_TYPED')),1)
        self.assertEqual(U.add(self.r.store,'Never delete my notes.','USER_TYPED')[0]['known'],True)  # no duplicate
        self.assertEqual(len(U.rules(self.r.store)),1)
    def test_G2_chat_text_never_loosens(self):
        U.observe(self.r.store,'Never delete my notes.');out=U.observe(self.r.store,'You can delete notes again now.')
        self.assertTrue(out and out[0].startswith('[Keine Regel gelockert]'));self.assertEqual(U.rules(self.r.store)[0]['status'],'ACTIVE')
        U.operator_command(self.r,['aus','R1']);self.assertEqual(U.rules(self.r.store)[0]['status'],'OFF')
    def test_G6_forbid_refuses_even_an_approved_call(self):
        self.reg.enable('sandbox_note');self.reg.approve(self.reg.call('sandbox_note',{'name':'plan','text':'old'},origin='USER')['id'])  # the note exists
        U.add(self.r.store,'Never overwrite my notes.','USER_TYPED')
        tx=self.reg.call('sandbox_note',{'name':'plan','text':'new'},origin='USER')
        self.assertEqual((tx['status'],tx['reason']),('DENIED','USER_RULE:R1'));self.assertEqual(tx['user_rules'][0]['text'],'Never overwrite my notes')
        self.assertEqual(self.reg._policy(self.reg.tools['sandbox_note'],'USER',{'name':'plan','text':'x'},confirmed=True)[0],'DENIED')
        tx=self.reg.call('sandbox_note',{'name':'fresh','text':'new'},origin='USER');self.assertEqual(tx['status'],'PROPOSED')  # a new note is no overwrite
    def test_ask_first_turns_automatic_run_into_proposal_and_approval_runs_it(self):
        self.reg.enable('calc');self.assertEqual(self.reg.call('calc',{'expression':'2+2'},origin='USER')['status'],'EXECUTED')
        U.add(self.r.store,'Tell me before you do anything.','USER_TYPED')
        tx=self.reg.call('calc',{'expression':'2+3'},origin='USER');self.assertEqual((tx['status'],tx['reason']),('PROPOSED','USER_RULE_ASK:R1'))
        self.assertEqual(self.reg.approve(tx['id'])['status'],'EXECUTED')
    def test_operator_records_rule_before_the_turn_with_fixed_notice(self):
        op=Operator(self.r);submitted=[];self.r.submit=lambda line:submitted.append(line) or 'evt'
        op.run('Lösch bitte niemals meine Notizen.')
        self.assertEqual(submitted,['Lösch bitte niemals meine Notizen.']);self.assertEqual(len(U.rules(self.r.store)),1)
        self.assertTrue(self.notes[0].startswith('[Regel R1 gespeichert] Verbot: löschen'));self.assertIn(':regel aus R1',self.notes[0])
        op.run('Maybe don\'t send that email yet.');self.assertTrue(self.notes[-1].startswith('[Rückfrage R2]'))
        self.assertEqual(U.rules(self.r.store)[1]['status'],'OPEN')
        self.assertIn('Verbot',op.run(':regel verbot R2'));self.assertEqual(U.rules(self.r.store)[1]['kind'],'FORBID')
        rep=json.loads(op.run(':regeln'));self.assertEqual(len(rep['deine_regeln']),2);self.assertTrue(rep['grundregeln'])
        self.assertIn('calc',rep['was_ich_tun_wuerde'])
        self.assertEqual(op.run(':regel Hallo'),'Keine Regel erkannt. Beispiel: :regel Lösch niemals meine Notizen.')
    def test_live_turn_plan_forbidden_tool_is_not_even_shadowed(self):
        self.reg.enable('calc');U.add(self.r.store,"Don't use the calculator.",'USER_TYPED')
        e=self.r.store.event(self.r.session,'What is 17 * 23?');ts=T.ToolStep(self.r);p=ts.plan(e,'What is 17 * 23?')
        self.assertEqual((p['status'],p['reason']),('DENIED','USER_RULE:R1'));self.assertIsNone(ts.shadow(e,p))
        text=rule_notice_text('calc',U.texts_for(self.r.store,p['reason']))
        self.assertIn("„Don't use the calculator“",text);self.assertTrue(text.startswith('[Nicht getan]'))
    def test_live_turn_ask_rule_becomes_visible_proposal(self):
        self.reg.enable('calc');U.add(self.r.store,'Tell me before you do anything.','USER_TYPED')
        e=self.r.store.event(self.r.session,'What is 17 * 23?');ts=T.ToolStep(self.r);p=ts.plan(e,'What is 17 * 23?')
        self.assertEqual(p['status'],'PROPOSED')  # Age 0 would only shadow it; the rule makes it a visible question instead
        pend=ts.propose_call(e,p);text=preview_text(pend)
        self.assertIn('Vorhaben: calc',text);self.assertIn('„Tell me before you do anything“',text);self.assertIn(':tx approve '+pend['call_id'],text)
    def test_no_rules_no_change(self):
        self.reg.enable('calc');self.assertEqual(self.reg.call('calc',{'expression':'2+2'},origin='USER')['status'],'EXECUTED')
        e=self.r.store.event(self.r.session,'What is 17 * 23?');p=T.ToolStep(self.r).plan(e,'What is 17 * 23?')
        self.assertNotIn('USER_RULE',p['reason'])

if __name__=='__main__':unittest.main()
