"""Run73: Context OS exact_recent_pin must never silently compress/drop RAW turns."""
import copy
import unittest
from v13.context_os import ContextOS


class FakeStore:
    generation_id='gen-test'
    def __init__(self):
        self.st=None
        self.version=0
        self.packets=[]
    def state(self,key,default=None):
        return (copy.deepcopy(self.st) if self.st is not None else default,self.version)
    def set_state(self,key,value,expected=None):
        if expected is not None and expected!=self.version:
            raise ValueError('Stale state')
        self.st=copy.deepcopy(value)
        self.version+=1
    def one(self,query,args=()):
        if 'MAX(rowid)' in query:
            return {'n':0}
        raise AssertionError(query)
    def add_packet(self,kind,p):
        self.packets.append((kind,p))
        return p


def history(n=5,chars=150):
    out=[]
    for i in range(n):
        out.append({'event_id':'turn'+str(i),'role':'user','text':('user'+str(i)+' '+('x'*chars))})
        out.append({'event_id':'turn'+str(i),'role':'assistant','text':('assistant'+str(i)+' '+('y'*chars))})
    return out


def plan(active=True,context_tokens=100,stable='SYSTEM',turns=None):
    s=FakeStore()
    os=ContextOS(s,{'context_tokens':context_tokens,'answer_tokens':10})
    if active:os.set_mode('ACTIVE',authority='EXPLICIT_HUMAN')
    result=os.plan('new-event','B1_DETAIL',stable,[],history() if turns is None else turns,'What is the answer?')
    return result


class ContextExactPin(unittest.TestCase):
    def test_pinned_turns_remain_raw_under_budget_pressure(self):
        p=plan()
        pinned=[x for x in p['plan']['items'] if x.get('pinned')]
        self.assertEqual(len(pinned),4)
        self.assertTrue(all(x['form']=='RAW' for x in pinned),pinned)

    def test_active_plan_fails_closed_when_exact_pin_cannot_fit(self):
        p=plan()
        self.assertFalse(p['applied'])
        self.assertIn('budget_unmet_fallback',p['plan']['decisions'])
        self.assertEqual(p['plan']['cache']['fallback_reason'],'exact_pin_budget_unmet')
        self.assertEqual(p['messages'],p['legacy'])

    def test_generous_budget_retains_active_utility(self):
        p=plan(context_tokens=4096)
        self.assertTrue(p['applied'])
        self.assertTrue(all(x['form']=='RAW' for x in p['plan']['items'] if x.get('pinned')))

    def test_shadow_never_applies(self):
        p=plan(active=False,context_tokens=4096)
        self.assertFalse(p['applied'])
        self.assertEqual(p['messages'],p['legacy'])

    def test_single_pinned_turn_larger_than_budget_fails_closed(self):
        p=plan(turns=history(1,chars=500))
        self.assertFalse(p['applied'])
        self.assertEqual([x['form'] for x in p['plan']['items'] if x.get('pinned')],['RAW'])

    def test_exact_numeric_code_in_pinned_turn_remains_verbatim(self):
        turns=history(5,chars=100)
        turns[-2]['text']='Pinned exact number 123456789 and code `x=42` '+('z'*300)
        p=plan(turns=turns)
        self.assertTrue(any('123456789' in m['content'] and '`x=42`' in m['content'] for m in p['planned']))
        self.assertFalse(p['applied'])


if __name__=='__main__':unittest.main()
