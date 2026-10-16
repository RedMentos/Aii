"""Synthetic integrity regressions; no models or native learning-gain claim."""
import copy
import json
from pathlib import Path
import unittest
from unittest import mock

from scripts import tool_forecast_learning_integrity_candidate as checked

CALC = ('double', 'add_15', 'quarter', 'subtract_7')
NOTE = ('append_done', 'prefix_urgent', 'uppercase')


def fixture(plan_doc=None):
    plan_doc = copy.deepcopy(plan_doc) if plan_doc is not None else {
        'schema': 'v13-tool-forecast-learning-plan-v1', 'round': 2, 'mode': 'region',
        'plan': {'calc_shift_exp': [1001], 'calc_shift_test': [1002], 'calc_in_test': [12],
                 'note_shift_exp': ['New training note.'], 'note_shift_test': ['New testing note.'],
                 'note_in_test': ['Call grandma on Monday.']}}
    plan = plan_doc['plan']
    rows = []
    for arm in ('calc_shift_exp', 'note_shift_exp', 'calc_shift_test', 'calc_in_test', 'note_shift_test', 'note_in_test'):
        for state in plan[arm]:
            for action in CALC if arm.startswith('calc_') else NOTE:
                i = len(rows) + 1
                mse = {'forecast': 1., 'copy': 2., 'mean_delta': 2.}
                if not arm.endswith('_exp'):
                    mse['adapted'] = .5 if '_shift_' in arm else 1.
                rows.append({'arm': arm, 'action': action, 'state': state, 'status': 'SCORED',
                             'tool_status': 'EXECUTED', 'call': 'tool_' + format(i, '032x'),
                             'forecast_id': 'tfc_' + format(i, '032x'), 'mse': mse})
    learn = {'calc_counter': {'pass': True, 'experience_rows': len(plan['calc_shift_exp']) * 4,
                              'adapted_actions': list(CALC)},
             'note_edit': {'pass': True, 'experience_rows': len(plan['note_shift_exp']) * 3,
                           'adapted_actions': list(NOTE)}}
    return rows, learn, plan_doc


class LearningIntegrity(unittest.TestCase):
    def assertRejected(self, rows, learn, plan, code):
        with mock.patch.object(checked.original, 'analyze') as analyze:
            result = checked.analyze_checked(rows, learn, plan)
        self.assertFalse(result['integrity']['pass'], result)
        self.assertFalse(result['analysis_ran'])
        self.assertEqual(result['verdict'], checked.NOT_CONFIRMED)
        self.assertIn(code, [error['code'] for error in result['integrity']['errors']])
        analyze.assert_not_called()
        return result

    def test_original_partial_false_pass_is_blocked_before_original_analysis(self):
        rows, learn, plan = fixture()
        rows = [row for row in rows if not row['arm'].endswith('_exp')
                and row['action'] in ('double', 'append_done')]
        self.assertEqual(len(rows), 4)
        self.assertEqual(checked.original.analyze(rows, learn)['verdict'], 'CONTINUAL_LEARNING_CONFIRMED')
        result = self.assertRejected(rows, learn, plan, 'MISSING_CASES')
        self.assertEqual(result['integrity']['expected_rows'], 21)
        self.assertEqual(len(result['integrity']['missing_cases']), 17)

    def test_complete_fixture_delegates_to_original_without_changing_numeric_gates(self):
        rows, learn, plan = fixture()
        expected = checked.original.analyze([row for row in rows if not row['arm'].endswith('_exp')], learn)
        with mock.patch.object(checked.original, 'analyze', wraps=checked.original.analyze) as analyze:
            result = checked.analyze_checked(rows, learn, plan)
        analyze.assert_called_once()
        self.assertTrue(result['integrity']['pass'])
        self.assertTrue(result['analysis_ran'])
        self.assertEqual(result['worlds'], expected['worlds'])
        self.assertEqual(result['verdict'], expected['verdict'])
        self.assertEqual(result['gates'], {'shift_gain_max_ratio': .90, 'in_world_max_ratio': 1.02})
        self.assertFalse(result['canonical_gate_pass'])
        self.assertFalse(result['phone_measured'])

    def test_actual_fixed_plan_grid_is_610_rows_250_experience_and_360_test(self):
        doc = json.loads((Path(__file__).resolve().parents[1] / 'specs/tool_forecast/learning-plan.json').read_text())
        rows, learn, plan = fixture(doc)
        result = checked.analyze_checked(rows, learn, plan)
        integrity = result['integrity']
        self.assertTrue(integrity['pass'], integrity)
        self.assertEqual(integrity['expected_rows'], 610)
        self.assertEqual(integrity['experience_rows'], 250)
        self.assertEqual(integrity['test_rows'], 360)
        self.assertEqual(integrity['expected_by_arm'], {'calc_shift_exp': 160, 'note_shift_exp': 90,
            'calc_shift_test': 120, 'calc_in_test': 120, 'note_shift_test': 60, 'note_in_test': 60})

    def test_missing_action_cannot_shrink_majority_denominator(self):
        rows, learn, plan = fixture()
        rows = [row for row in rows if not (row['arm'] == 'calc_shift_test' and row['action'] != 'double')]
        self.assertRejected(rows, learn, plan, 'MISSING_CASES')

    def test_missing_retention_case_cannot_shrink_all_action_gate(self):
        rows, learn, plan = fixture()
        rows = [row for row in rows if not (row['arm'] == 'note_in_test' and row['action'] == 'uppercase')]
        self.assertRejected(rows, learn, plan, 'MISSING_CASES')

    def test_duplicate_case_with_new_ids_is_rejected(self):
        rows, learn, plan = fixture()
        rows[-1] = copy.deepcopy(rows[-2])
        rows[-1]['call'] = 'tool_' + 'f' * 32
        rows[-1]['forecast_id'] = 'tfc_' + 'f' * 32
        self.assertRejected(rows, learn, plan, 'DUPLICATE_CASE')

    def test_reused_call_or_forecast_across_distinct_cases_rejected(self):
        for key in ('call', 'forecast_id'):
            with self.subTest(key=key):
                rows, learn, plan = fixture()
                rows[1][key] = rows[0][key]
                self.assertRejected(rows, learn, plan, 'REUSED_ID')

    def test_invalid_ids_rejected(self):
        for key in ('call', 'forecast_id'):
            for value in (None, '', 'bad-id', [], True):
                with self.subTest(key=key, value=value):
                    rows, learn, plan = fixture()
                    rows[0][key] = value
                    self.assertRejected(rows, learn, plan, 'INVALID_ID')

    def test_failed_pending_or_unexecuted_rows_not_dropped(self):
        for key, value, code in (('status', 'PENDING', 'ROW_NOT_SCORED'),
                                 ('status', 'OBSERVE_FAILED', 'ROW_NOT_SCORED'),
                                 ('tool_status', 'FAILED', 'CALL_NOT_EXECUTED')):
            with self.subTest(key=key, value=value):
                rows, learn, plan = fixture()
                rows[0][key] = value
                self.assertRejected(rows, learn, plan, code)

    def test_mse_must_be_finite_nonnegative_number(self):
        for metric in ('forecast', 'copy', 'mean_delta', 'adapted'):
            for value in (float('nan'), float('inf'), float('-inf'), 10 ** 400, -1., True, '0.1', None):
                with self.subTest(metric=metric, value=value):
                    rows, learn, plan = fixture()
                    rows[-1]['mse'][metric] = value
                    self.assertRejected(rows, learn, plan, 'INVALID_MSE_VALUE')

    def test_missing_adapted_after_successful_learn_is_not_measured_fallback(self):
        rows, learn, plan = fixture()
        del rows[-1]['mse']['adapted']
        self.assertRejected(rows, learn, plan, 'MISSING_MSE')

    def test_missing_or_invalid_base_mse_is_rejected(self):
        for metric in ('forecast', 'copy', 'mean_delta'):
            with self.subTest(metric=metric):
                rows, learn, plan = fixture()
                del rows[0]['mse'][metric]
                self.assertRejected(rows, learn, plan, 'MISSING_MSE')
        rows, learn, plan = fixture()
        rows[0]['mse'] = None
        self.assertRejected(rows, learn, plan, 'INVALID_MSE')

    def test_missing_unknown_or_duplicate_adapted_actions_are_rejected(self):
        for adapted, code in ((None, 'INVALID_ADAPTED_ACTIONS'), (['unknown'], 'INVALID_ADAPTED_ACTIONS'),
                               (['double', 'double'], 'INVALID_ADAPTED_ACTIONS'), ([], 'ADAPTED_ACTIONS_PASS_MISMATCH')):
            with self.subTest(adapted=adapted):
                rows, learn, plan = fixture()
                learn['calc_counter']['adapted_actions'] = adapted
                self.assertRejected(rows, learn, plan, code)

    def test_learn_report_worlds_and_experience_counts_are_required(self):
        rows, learn, plan = fixture()
        del learn['note_edit']
        self.assertRejected(rows, learn, plan, 'INVALID_LEARN_REPORT')
        rows, learn, plan = fixture()
        learn['calc_counter']['experience_rows'] = 3
        self.assertRejected(rows, learn, plan, 'EXPERIENCE_COUNT_MISMATCH')

    def test_valid_failed_learning_still_does_not_confirm(self):
        rows, learn, plan = fixture()
        learn['calc_counter']['pass'] = False
        learn['calc_counter']['adapted_actions'] = []
        for row in rows:
            if row['arm'].startswith('calc_'):
                row['mse'].pop('adapted', None)
        result = checked.analyze_checked(rows, learn, plan)
        self.assertTrue(result['integrity']['pass'])
        self.assertEqual(result['verdict'], checked.NOT_CONFIRMED)

    def test_unplanned_action_state_and_arm_rejected(self):
        for key, value, code in (('action', 'other', 'INVALID_CASE'),
                                 ('state', 9998, 'UNPLANNED_CASE'), ('arm', 'extra', 'UNEXPECTED_ARM')):
            with self.subTest(key=key):
                rows, learn, plan = fixture()
                rows[0][key] = value
                self.assertRejected(rows, learn, plan, code)

    def test_plan_omissions_empty_arms_and_state_collisions_rejected(self):
        for mutation in ('omit', 'empty', 'duplicate', 'across_arms', 'wrong_type'):
            with self.subTest(mutation=mutation):
                rows, learn, plan = fixture()
                if mutation == 'omit': del plan['plan']['calc_in_test']
                if mutation == 'empty': plan['plan']['calc_in_test'] = []
                if mutation == 'duplicate': plan['plan']['calc_in_test'] = [12, 12]
                if mutation == 'across_arms': plan['plan']['calc_shift_test'] = [1001]
                if mutation == 'wrong_type': plan['plan']['calc_in_test'] = [True]
                self.assertRejected(rows, learn, plan, 'INVALID_PLAN')

    def test_malformed_case_types_do_not_alias_integer_state(self):
        rows, learn, plan = fixture()
        rows[0]['state'] = float(rows[0]['state'])
        self.assertRejected(rows, learn, plan, 'INVALID_CASE')

    def test_phase_a_cannot_follow_phase_b(self):
        rows, learn, plan = fixture()
        rows.append(rows.pop(0))
        self.assertRejected(rows, learn, plan, 'EXPERIENCE_AFTER_TEST')

    def test_original_strict_majority_and_ratio_thresholds_unchanged(self):
        rows, learn, plan = fixture()
        for row in rows:
            if row['arm'] == 'calc_shift_test':
                row['mse']['adapted'] = .5 if row['action'] in CALC[:2] else 1.
        result = checked.analyze_checked(rows, learn, plan)
        self.assertTrue(result['integrity']['pass'])
        self.assertEqual(result['verdict'], checked.NOT_CONFIRMED)
        for row in rows:
            if row['arm'] == 'calc_shift_test': row['mse']['adapted'] = .90
        self.assertEqual(checked.analyze_checked(rows, learn, plan)['verdict'], checked.NOT_CONFIRMED)
        for row in rows:
            if row['arm'] == 'calc_shift_test': row['mse']['adapted'] = .89
            if row['arm'] == 'note_in_test': row['mse']['adapted'] = 1.02
        self.assertEqual(checked.analyze_checked(rows, learn, plan)['verdict'], 'CONTINUAL_LEARNING_CONFIRMED')
        rows[-1]['mse']['adapted'] = 1.0201
        self.assertEqual(checked.analyze_checked(rows, learn, plan)['verdict'], checked.NOT_CONFIRMED)

    def test_zero_mse_is_valid_but_undefined_original_ratio_cannot_confirm(self):
        rows, learn, plan = fixture()
        for row in rows:
            if row['arm'] == 'calc_shift_test': row['mse']['forecast'] = 0.
        result = checked.analyze_checked(rows, learn, plan)
        self.assertTrue(result['integrity']['pass'])
        self.assertTrue(result['analysis_ran'])
        self.assertEqual(result['verdict'], checked.NOT_CONFIRMED)
        self.assertEqual(result['analysis_error']['code'], 'ORIGINAL_ANALYSIS_UNDEFINED')


if __name__ == '__main__':
    unittest.main()
