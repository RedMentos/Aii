"""End-to-end AG10 generated-tool registration with real V13 Runtime/SQLite."""
from pathlib import Path
import tempfile
import unittest
from v13.runtime import Runtime
from v13.agi import hub


class GeneratedToolRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        self.runtime=Runtime(self.home)
        self.runtime.sleep.cycle.set_policy('enabled','off')
        self.runtime.sleep.cycle.set_policy('tick_seconds','300')

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def test_generate_activate_enable_execute_and_reopen(self):
        g=hub(self.runtime)
        examples=[[x,x+7] for x in (-8,-5,0,3,12,18)]
        g.tool_builder.propose('plus_seven',examples,origin='SELF')
        self.assertNotIn('plus_seven',g.tools.tools)
        with self.assertRaises(PermissionError):g.tool_builder.activate('plus_seven',origin='SELF')
        g.tool_builder.activate('plus_seven',origin='USER')
        self.assertFalse(g.tools.report()['tools']['plus_seven']['enabled'])
        # ToolRegistry's normal opt-in and transactional call path still apply.
        denied=g.tools.call('plus_seven',{'x':5},origin='USER')
        self.assertNotEqual(denied['status'],'EXECUTED')
        g.tools.enable('plus_seven')
        executed=g.tools.call('plus_seven',{'x':5},origin='USER')
        self.assertEqual(executed['status'],'EXECUTED')
        self.assertEqual(executed['result'],12)
        self.runtime.close()
        self.runtime=Runtime(self.home)
        self.runtime.sleep.cycle.set_policy('enabled','off')
        self.runtime.sleep.cycle.set_policy('tick_seconds','300')
        reopened=hub(self.runtime)
        self.assertIn('plus_seven',reopened.tools.tools)
        self.assertTrue(reopened.tools.report()['tools']['plus_seven']['enabled'])
        after=reopened.tools.call('plus_seven',{'x':-2},origin='USER')
        self.assertEqual(after['status'],'EXECUTED')
        self.assertEqual(after['result'],5)

    def test_generated_text_tool_executes_via_registry(self):
        g=hub(self.runtime)
        g.tool_builder.propose_text('uppercase',[[x,x.upper()] for x in ('alpha','beta','gamma','delta','epsilon','zeta')])
        g.tool_builder.activate('uppercase')
        g.tools.enable('uppercase')
        result=g.tools.call('uppercase',{'x':'hello'},origin='USER')
        self.assertEqual(result['status'],'EXECUTED')
        self.assertEqual(result['result'],'HELLO')

    def test_retire_revokes_enabled_tool_across_restart(self):
        g=hub(self.runtime)
        g.tool_builder.propose('plus_seven',[[x,x+7] for x in (-8,-5,0,3,12,18)])
        g.tool_builder.activate('plus_seven')
        g.tools.enable('plus_seven')
        g.tool_builder.retire('plus_seven')
        self.assertNotIn('plus_seven',g.tools.tools)
        self.runtime.close()
        self.runtime=Runtime(self.home)
        self.runtime.sleep.cycle.set_policy('enabled','off')
        self.runtime.sleep.cycle.set_policy('tick_seconds','300')
        reopened=hub(self.runtime)
        self.assertNotIn('plus_seven',reopened.tools.tools)

    def test_learns_new_tool_from_real_successful_tool_transactions(self):
        from v13.agi.tools import ToolSpec
        g=hub(self.runtime)
        g.tools.register(ToolSpec('example_source',lambda x:x+7,risk='READ_LOCAL',
            schema={'x':'int'},effects=({'COMPUTE'},{'CALCULATOR'})))
        g.tools.enable('example_source')
        for x in (-8,-5,0,3,12,18):
            tx=g.tools.call('example_source',{'x':x},origin='USER')
            self.assertEqual(tx['status'],'EXECUTED')
        p=g.tool_builder.propose_from_tool_history('learned_from_experience','example_source')
        self.assertEqual(p['program'],'add:7')
        self.assertNotIn('learned_from_experience',g.tools.tools)
        g.tool_builder.activate('learned_from_experience')
        g.tools.enable('learned_from_experience')
        tx=g.tools.call('learned_from_experience',{'x':100},origin='USER')
        self.assertEqual(tx['status'],'EXECUTED')
        self.assertEqual(tx['result'],107)

    def test_generated_tool_cannot_bypass_age_zero_self_action_right(self):
        g=hub(self.runtime)
        g.tool_builder.propose('plus_seven',[[x,x+7] for x in (-8,-5,0,3,12,18)])
        g.tool_builder.activate('plus_seven')
        g.tools.enable('plus_seven')
        result=g.tools.call('plus_seven',{'x':5},origin='SELF')
        self.assertNotEqual(result['status'],'EXECUTED')

    def test_generated_tool_does_not_accept_wrong_schema(self):
        g=hub(self.runtime)
        g.tool_builder.propose('double',[[x,2*x] for x in (1,3,5,7,9,11)])
        g.tool_builder.activate('double')
        g.tools.enable('double')
        bad=g.tools.call('double',{'x':'not-an-int'},origin='USER')
        self.assertEqual(bad['status'],'DENIED')
