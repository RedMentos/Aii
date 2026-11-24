"""Zero-native tests for read-only private pilot evidence auditing."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from audit_private_pilot import audit, canonical, digest, ARMS, DELIVERY, IDS, ACTIONS, REG_SCHEMA, REPORT_SCHEMA, SCOPE


class PilotAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.fixture = {'scope': SCOPE, 'gate_promotion': False, 'native_runs': 0,
                        'selected_ids': list(IDS), 'fixtures': [
                            {'id': fid, 'kind': 'complementary', 'oracle': {'action': action}}
                            for fid, action in zip(IDS, ACTIONS)]}
        self.reg = {
            'schema': REG_SCHEMA, 'status': 'REGISTERED_NOT_RUN', 'scope': SCOPE,
            'gate_promotion': False, 'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED',
            'numeric_utility_gate': 'NO_UTILITY_PROMOTION_FOR_DIAGNOSTIC_PILOT',
            'fixture_ids': list(IDS), 'variant_order': list(ARMS),
            'variants': {k: {'roles': v, 'delivery': DELIVERY[k]} for k, v in ARMS.items()},
            'row_order': [[fid, arm] for fid in IDS for arm in ARMS],
            'max_rows': 18, 'max_native_calls': 42, 'max_total_row_seconds': 1620,
            'row_seconds': 90, 'producer_tokens': 256, 'consumer_tokens': 256,
            'config': {'learning_mode': 'RECORD_ONLY', 'teacher_enabled': False, 'seed': 13},
            'device': {'android': False},
            'source_bindings': {'v13/a.py': digest('a'), 'v13/b.py': digest('b'), 'v13/c.py': digest('c')},
            'installed_bindings': {'models': {role: {'path': '/missing/' + role,
                'sha256': digest(role)} for role in ('B1_DETAIL', 'B2_GIST', 'C3_LANGUAGE')},
                'runner': {'path': '/missing/llama-server', 'sha256': digest('runner')},
                'runtime_libraries': {}, 'models_manifest_sha256': digest('manifest')},
        }
        self.fixpath = self.base / 'pilot.json'
        self.regpath = self.base / 'registration.json'
        self.save_inputs()

    def save_inputs(self):
        self.reg['fixtures_sha256'] = digest(canonical(self.fixture))
        self.fixpath.write_text(canonical(self.fixture))
        self.regpath.write_text(canonical(self.reg))

    def valid_run(self):
        folder = self.base / 'run'
        folder.mkdir()
        (folder / 'registration.json').write_text(canonical(self.reg))
        rows = []
        for fid in IDS:
            for arm, roles in ARMS.items():
                expected = roles + ['C3_LANGUAGE']
                row = {'fixture': fid, 'variant': arm, 'status': 'RECORDED',
                       'gate_promotion': False, 'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED',
                       'processes_reaped': True,
                       'calls': [{'role': role, 'status': 'FINAL', 'metrics': {'status': 'FINAL'},
                                  'max_tokens': 256, 'seed': 13} for role in expected],
                       'process_releases': [{'role': role, 'process_reaped': True} for role in expected]}
                rows.append(row)
                (folder / (fid + '__' + arm + '.json')).write_text(canonical(row))
        report = {'schema': REPORT_SCHEMA, 'scope': SCOPE, 'status': 'RECORDED',
                  'registration_sha256': digest(canonical(self.reg)),
                  'coverage_complete': True, 'final_bindings_unchanged': True,
                  'gate_promotion': False, 'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED',
                  'evidence_level': 'NATIVE_RUNNER_BOUNDARY', 'phone_measured': False,
                  'rows': rows, 'row_sha256': {r['fixture'] + ':' + r['variant']: digest(canonical(r)) for r in rows}}
        (folder / 'report.json').write_text(canonical(report))
        return folder, report

    def test_saved_registration_is_prepared_not_native_pass(self):
        result = audit(self.regpath, self.fixpath)
        self.assertEqual(result['status'], 'PREPARED_NOT_RUN')
        self.assertEqual(result['native_model_runs'], 0)
        self.assertFalse(result['gate_promotion'])
        self.assertIn('SOURCE_BYTES_NOT_RECHECKED', result['unverified'])

    def test_complete_artifact_consistency_still_does_not_promote_utility(self):
        folder, _ = self.valid_run()
        result = audit(self.regpath, self.fixpath, folder)
        self.assertEqual(result['status'], 'ARTIFACT_CONSISTENCY_PASS_NOT_QUALITY_GATE')
        self.assertEqual(result['rows_audited'], 18)
        self.assertEqual(result['native_model_runs'], 0)
        self.assertFalse(result['gate_promotion'])
        self.assertIn('UTILITY_SCORE_NOT_INDEPENDENTLY_RECOMPUTED', result['unverified'])

    def test_registration_mutations_are_refused(self):
        for key, value in [('max_native_calls', 43), ('status', 'RECORDED'),
                           ('gate_promotion', True), ('row_order', []),
                           ('fixture_ids', [IDS[0]]), ('historical_step2_utility', 'PASS'),
                           ('variants', {}), ('scope', 'FULL_STEP2_PASS')]:
            with self.subTest(key=key):
                original = copy.deepcopy(self.reg[key]); self.reg[key] = value
                self.save_inputs()
                self.assertEqual(audit(self.regpath, self.fixpath)['status'], 'REFUSED')
                self.reg[key] = original
        self.save_inputs()

    def test_fixture_hash_and_geometry_are_checked(self):
        self.fixture['fixtures'][0]['oracle']['action'] = 'B'
        self.fixpath.write_text(canonical(self.fixture))
        result = audit(self.regpath, self.fixpath)
        self.assertIn('FIXTURE_HASH', result['errors'])
        self.assertIn('FIXTURE_GEOMETRY', result['errors'])

    def test_rejects_duplicate_json_keys_and_nonfinite_constants(self):
        self.regpath.write_text('{"schema":1,"schema":2}')
        self.assertEqual(audit(self.regpath, self.fixpath)['status'], 'REFUSED')
        self.regpath.write_text('{"a":NaN}')
        self.assertEqual(audit(self.regpath, self.fixpath)['status'], 'REFUSED')

    def test_source_hashes_can_be_checked_without_native_weights(self):
        root = self.base / 'code'
        (root / 'v13').mkdir(parents=True)
        for name, data in [('a', 'a'), ('b', 'b'), ('c', 'c')]:
            (root / 'v13' / (name + '.py')).write_text(data)
        self.assertEqual(audit(self.regpath, self.fixpath, source_root=root)['status'], 'PREPARED_NOT_RUN')
        (root / 'v13/b.py').write_text('changed')
        self.assertIn('SOURCE_HASH_MISMATCH:v13/b.py',
                      audit(self.regpath, self.fixpath, source_root=root)['errors'])

    def test_run_mutations_refused(self):
        for mutation, code in [('missing_row', 'RUN_ROW_COUNT'), ('swap_file', 'ROW_FILE_DIFFERS:'),
                               ('wrong_role', 'CALL_ROLE_ORDER:'), ('missing_release', 'PROCESS_RELEASE_BINDING:'),
                               ('nonfinal', 'CALL_NOT_FINAL:'), ('wrong_budget', 'CALL_BUDGET_SEED:'),
                               ('hash', 'ROW_HASH:'), ('promotion', 'RUN_GATE_CHANGED'),
                               ('device', 'RUN_DEVICE_CONFLICT'), ('status', 'RUN_NOT_COMPLETED')]:
            with self.subTest(mutation=mutation):
                folder, report = self.valid_run() if not (self.base / 'run').exists() else (self.base / 'run', None)
                if report is None:
                    report = json.loads((folder / 'report.json').read_text())
                row = report['rows'][0]
                if mutation == 'missing_row': report['rows'].pop()
                elif mutation == 'swap_file':
                    (folder / (row['fixture'] + '__' + row['variant'] + '.json')).write_text('{}')
                elif mutation == 'wrong_role': row['calls'][0]['role'] = 'C3_LANGUAGE'
                elif mutation == 'missing_release': row['process_releases'].pop()
                elif mutation == 'nonfinal': row['calls'][0]['status'] = 'RUNNING'
                elif mutation == 'wrong_budget': row['calls'][0]['max_tokens'] = 999
                elif mutation == 'hash': report['row_sha256'][row['fixture'] + ':' + row['variant']] = '0'*64
                elif mutation == 'promotion': report['gate_promotion'] = True
                elif mutation == 'device': report['phone_measured'] = True
                elif mutation == 'status': report['status'] = 'INTERRUPTED'
                (folder / 'report.json').write_text(canonical(report))
                result = audit(self.regpath, self.fixpath, folder)
                self.assertEqual(result['status'], 'REFUSED')
                self.assertTrue(any(x.startswith(code) for x in result['errors']), result['errors'])
                for p in folder.iterdir(): p.unlink()
                folder.rmdir()

    def test_absent_run_and_missing_model_bytes_do_not_get_native_pass(self):
        self.assertEqual(audit(self.regpath, self.fixpath, self.base / 'missing')['status'], 'REFUSED')
        result = audit(self.regpath, self.fixpath, installed_home=self.base)
        self.assertEqual(result['status'], 'REFUSED')
        self.assertTrue(any(x.startswith('INSTALLED_HASH_MISMATCH:') for x in result['errors']))

    def test_cli_writes_bounded_nonpromoting_preflight_and_refuses_overwrite(self):
        from audit_private_pilot import main
        output = self.base / 'audit.json'
        self.assertEqual(main(['--registration', str(self.regpath), '--fixtures', str(self.fixpath),
                               '--out', str(output)]), 0)
        result = json.loads(output.read_text())
        self.assertEqual(result['status'], 'PREPARED_NOT_RUN')
        self.assertFalse(result['gate_promotion'])
        with self.assertRaises(SystemExit):
            main(['--registration', str(self.regpath), '--fixtures', str(self.fixpath),
                  '--out', str(output)])

    def test_malformed_optional_structures_are_refused_not_crashes(self):
        for field, value in [('config', None), ('device', None), ('row_seconds', None),
                             ('source_bindings', []), ('installed_bindings', None)]:
            with self.subTest(field=field):
                old = copy.deepcopy(self.reg[field]); self.reg[field] = value
                self.save_inputs()
                self.assertEqual(audit(self.regpath, self.fixpath)['status'], 'REFUSED')
                self.reg[field] = old
        self.save_inputs()

    def test_rejects_untrusted_source_path_escape(self):
        self.reg['source_bindings']['../escape.py'] = digest('x')
        self.save_inputs()
        result = audit(self.regpath, self.fixpath, source_root=self.base)
        self.assertIn('SOURCE_HASH_MISMATCH:../escape.py', result['errors'])


if __name__ == '__main__':
    unittest.main()
