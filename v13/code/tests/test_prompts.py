import unittest
from v13 import prompts
from v13.config import DEFAULTS,validate

class EnglishFirstPrompts(unittest.TestCase):
    def test_default_is_english_and_german_stays_selectable(self):
        self.assertEqual(DEFAULTS['answer_language'],'en')
        self.assertIn('Answer in English',prompts.text(DEFAULTS,'system'))
        self.assertIn('auf Deutsch',prompts.text(DEFAULTS|{'answer_language':'de'},'system'))
        with self.assertRaises(ValueError):validate(dict(DEFAULTS,answer_language='fr'))
    def test_both_languages_define_the_same_keys(self):
        self.assertEqual(set(prompts.TEXT['en']),set(prompts.TEXT['de']))
        self.assertEqual(len(prompts.TEXT['en']['probe_fixtures']),len(prompts.TEXT['de']['probe_fixtures']))
    def test_production_code_has_no_hardcoded_german_answer_instruction(self):
        from pathlib import Path
        root=Path(prompts.__file__).parent
        for name in ('runtime.py','verification.py','proofs.py','__main__.py'):
            self.assertNotIn('auf Deutsch',(root/name).read_text(),name)

    def test_numeric_instruction_is_generic_and_does_not_pretend_tool_execution(self):
        for lang,marker in (('en','actual numeric result'),('de','tatsächliche Zahlenergebnis')):
            system=prompts.TEXT[lang]['system']
            self.assertIn(marker,system)
            self.assertNotIn('120',system)
            self.assertNotIn('60',system)
            self.assertIn('tools' if lang=='en' else 'Tools',system)
        self.assertEqual(DEFAULTS['answer_language'],'en')

class ConductAndPrivacy(unittest.TestCase):
    def test_internal_organ_offers_are_private_without_changing_receipt_prefixes(self):
        for lang, markers, expected_prefix in (
            ('en', ('Do not reveal', 'internal offers'), 'Internal hypotheses: '),
            ('de', ('nicht offenlegen', 'Interne Angebote'), 'Interne Hypothesen: '),
        ):
            cfg = DEFAULTS | {'answer_language': lang}
            system = prompts.text(cfg, 'system')
            for marker in markers:
                self.assertIn(marker, system)
            self.assertEqual(prompts.text(cfg, 'hypotheses'), expected_prefix)

    def test_conduct_rule_is_harm_based_and_open(self):
        for lang in ('en','de'):
            t=prompts.TEXT[lang]['conduct']
            self.assertTrue(('fiction' in t) or ('Fiktion' in t));self.assertTrue(('reason' in t) or ('Grund' in t))
    def test_telemetry_never_keeps_content_fields(self):
        from v13.store import telemetry_metrics
        kept=telemetry_metrics({'text':'geheim','output':'geheim','query':'geheim','messages':[{'content':'geheim'}],'note':'geheim','kind':'rating'})
        self.assertNotIn('geheim',str(kept));self.assertIn('kind',kept);self.assertNotIn('text',kept)


class ProbeOutputPrivacy(unittest.TestCase):
    def test_console_probe_rejects_non_native_report_and_ignores_oversized_metrics(self):
        from v13.verification import public_probe_summary
        with self.assertRaises(ValueError):
            public_probe_summary({'proof_kind': 'OTHER', 'roles': {'C3_LANGUAGE': {'actual_output': 'SECRET'}}})
        summary = public_probe_summary({
            'proof_kind': 'NATIVE_SMOKE',
            'status': 'SMOKE_PARTIAL',
            'effective_config': {'threads': 6, 'oversized_number': 10**1000},
            'roles': {},
        })
        self.assertEqual(summary['effective_config'], {'threads': 6})

    def test_console_probe_redacts_model_outputs_offers_and_control_payloads(self):
        import json
        from v13.verification import public_probe_summary

        report = {
            'proof_kind': 'NATIVE_SMOKE',
            'status': 'SMOKE_PASS',
            'phone_measured': True,
            'full_runner_proof': False,
            'model_revisions': {'C3_LANGUAGE': 'revision-c3'},
            'effective_config': {'threads': 6, 'answer_tokens': 48, 'private_setting': 'SECRET_CONFIG', 'oversized_number': 10**1000},
            'missing_proofs': ['B3 receiver utility'],
            'roles': {
                'C3_LANGUAGE': {
                    'ok': True,
                    'actual_output': 'SECRET_C3_OUTPUT',
                    'metrics': {
                        'status': 'FINAL', 'generated_tokens': 7, 'prompt_tokens': 18,
                        'prompt_preview': 'SECRET_PROMPT',
                    },
                },
                'B1_DETAIL': {
                    'ok': True,
                    'actual_output': 'SECRET_B1_OUTPUT',
                    'metrics': {'status': 'FINAL', 'generated_tokens': 3},
                    'structured_offer': {
                        'verified_quote_count': 1, 'rejected_quote_count': 0,
                        'actual': {'summary': 'SECRET_B1_HYPOTHESIS'},
                    },
                },
                'B2_GIST': {
                    'ok': True,
                    'structured_offer': {
                        'verified_quote_count': 2, 'rejected_quote_count': 1,
                        'actual': {'summary': 'SECRET_B2_HYPOTHESIS'},
                    },
                },
                'C2_CONTROL': {
                    'ok': True, 'embedding_dim': 3072,
                    'actual_control': {'answer': 'SECRET_CONTROL_PAYLOAD'},
                },
            },
        }

        summary = public_probe_summary(report)
        rendered = json.dumps(summary, sort_keys=True)
        for secret in (
            'SECRET_C3_OUTPUT', 'SECRET_B1_OUTPUT', 'SECRET_B1_HYPOTHESIS',
            'SECRET_B2_HYPOTHESIS', 'SECRET_CONTROL_PAYLOAD',
            'SECRET_PROMPT', 'SECRET_CONFIG',
        ):
            self.assertNotIn(secret, rendered)
        self.assertEqual(summary['roles']['B1_DETAIL']['offer']['verified_quote_count'], 1)
        self.assertEqual(summary['roles']['B2_GIST']['offer']['rejected_quote_count'], 1)
        self.assertEqual(summary['roles']['C3_LANGUAGE']['metrics']['generated_tokens'], 7)
        self.assertEqual(summary['effective_config']['threads'], 6)
        self.assertTrue(summary['redaction']['raw_artifact_retained_locally'])


    def test_probe_metadata_uses_closed_field_specific_allowlists(self):
        import json
        from v13.verification import public_probe_summary

        secret = 'SECRET_PROMPT_PATH_AND_MODEL_OUTPUT'
        digest = 'a' * 64
        summary = public_probe_summary({
            'proof_kind': 'NATIVE_SMOKE',
            'status': secret,
            'phone_measured': 'true',
            'full_runner_proof': True,
            'model_revisions': {'C3_LANGUAGE': secret, 'B1_DETAIL': digest},
            'missing_proofs': [secret, 'sustained thermal/energy'],
            'effective_config': {'threads': 6, secret: 7},
            'roles': {
                'C3_LANGUAGE': {
                    'ok': True,
                    'metrics': {
                        'status': secret,
                        'role': secret,
                        'last_phase': secret,
                        'error_kind': secret,
                        'stage_durations_s': {
                            secret: 1.0,
                            'prefill_to_first_token_s': 2.0,
                        },
                        'prompt_admission': {
                            'revision': secret,
                            'status': secret,
                            'removed_layers': [secret, 'C3_LAYER_TASK_CONTEXT'],
                        },
                    },
                },
            },
        })
        rendered = json.dumps(summary, sort_keys=True)
        self.assertNotIn(secret, rendered)
        self.assertEqual(summary['status'], 'UNKNOWN')
        self.assertFalse(summary['phone_measured'])
        self.assertEqual(summary['model_revisions'], {'B1_DETAIL': digest})
        self.assertEqual(summary['missing_proofs'], ['SUSTAINED_THERMAL_ENERGY'])
        metrics = summary['roles']['C3_LANGUAGE']['metrics']
        self.assertNotIn('status', metrics)
        self.assertNotIn('role', metrics)
        self.assertNotIn('last_phase', metrics)
        self.assertNotIn('error_kind', metrics)
        self.assertEqual(metrics['stage_durations_s'], {'prefill_to_first_token_s': 2.0})
        self.assertEqual(
            metrics['prompt_admission']['removed_layers'],
            ['C3_LAYER_TASK_CONTEXT'],
        )
        self.assertNotIn('revision', metrics['prompt_admission'])
        self.assertNotIn('status', metrics['prompt_admission'])

    def test_probe_summary_ignores_unhashable_metadata_values(self):
        from v13.verification import public_probe_summary

        summary = public_probe_summary({
            'proof_kind': 'NATIVE_SMOKE',
            'status': [],
            'missing_proofs': [[], {}],
            'roles': {
                'C3_LANGUAGE': {
                    'metrics': {
                        'status': [],
                        'role': {},
                        'last_phase': [],
                        'error_kind': {},
                        'stage_durations_s': {'load_s': []},
                        'prompt_admission': {
                            'status': {},
                            'removed_layers': [{}, []],
                        },
                    },
                },
            },
        })
        self.assertEqual(summary['status'], 'UNKNOWN')
        self.assertEqual(summary['missing_proofs'], [])
        metrics = summary['roles']['C3_LANGUAGE']['metrics']
        for key in ('status', 'role', 'last_phase', 'error_kind'):
            self.assertNotIn(key, metrics)
        self.assertEqual(metrics['stage_durations_s'], {})
        self.assertEqual(metrics['prompt_admission']['removed_layers'], [])
        self.assertNotIn('status', metrics['prompt_admission'])

    def test_probe_worker_exception_never_reaches_console_or_telemetry(self):
        import queue
        import threading
        from unittest.mock import patch
        from v13.runtime import Runtime

        secret = 'SECRET_NATIVE_STDERR_PROMPT_FRAGMENT'
        notices = []

        class Store:
            def __init__(self):
                self.entries = []

            def log(self, *args):
                self.entries.append(args)

        runtime = Runtime.__new__(Runtime)
        runtime.stop = threading.Event()
        runtime.paused = False
        runtime.lock = threading.Lock()
        runtime.wake = threading.Event()
        runtime.cancel_event = threading.Event()
        runtime.jobs = queue.Queue()
        runtime.jobs.put(('probe', 'native', 0, 0.0))
        runtime.queued_bytes = 0
        runtime.current = None
        runtime.status = 'Bereit'
        runtime.store = Store()
        runtime.notice = lambda value: (notices.append(value), runtime.stop.set())

        with patch('v13.verification.probe', side_effect=RuntimeError(secret)):
            runtime._worker()

        rendered = repr((notices, runtime.store.entries))
        self.assertNotIn(secret, rendered)
        self.assertEqual(notices, ['probe: PROBE_ERROR'])
        self.assertEqual(
            runtime.store.entries,
            [('job_error', None, {'kind': 'probe', 'error': 'PROBE_ERROR'})],
        )

    def test_one_shot_probe_exception_is_redacted(self):
        import contextlib
        import io
        from pathlib import Path
        from unittest.mock import patch
        import v13.__main__ as cli

        secret = 'SECRET_CLI_NATIVE_STDERR'
        output = io.StringIO()

        class RuntimeStub:
            def __init__(self, home, notice):
                self.closed = False

            def close(self):
                self.closed = True

        with patch.object(cli, 'home_path', return_value=Path('/tmp/v13-probe-privacy-test')), \
             patch.object(cli, 'initialize'), \
             patch('v13.backup.recover_startup'), \
             patch('v13.runtime.Runtime', RuntimeStub), \
             patch('v13.verification.probe', side_effect=RuntimeError(secret)), \
             contextlib.redirect_stdout(output):
            result = cli.main(['probe', 'native'])

        self.assertEqual(result, 2)
        self.assertIn('SMOKE_ERROR', output.getvalue())
        self.assertIn('PROBE_EXECUTION_ERROR', output.getvalue())
        self.assertNotIn(secret, output.getvalue())

if __name__=='__main__':unittest.main()
