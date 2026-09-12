import os
import sys
import unittest

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)
os.environ['WEFAQ_DATA_DIR'] = os.path.join(BACKEND_DIR, 'models', 'data')

from routes.user_routes import _valid_full_name, _validate_open_answers, _validate_profile_details
from utils import load_questions


class OnboardingConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.questions = load_questions()
        self.flow = self.questions['onboarding']['flow']
        self.valid_details = {
            'registrant_relation': 'أنا صاحب الطلب',
            'nationality': 'قطري',
            'profession': 'مهندس',
            'marital_status': 'أعزب',
            'marriage_timeline': '3 أشهر',
            'height': 175,
            'weight': 75,
            'skin_tone': 'قمحي',
            'body_type': 'رياضي',
            'nationality_preference': ['قطري', 'سعودي'],
        }

    def test_final_flow_has_expected_logical_order(self):
        self.assertLess(self.flow.index('registrant_relation'), self.flow.index('full_name'))
        self.assertLess(self.flow.index('nationality'), self.flow.index('country'))
        self.assertLess(self.flow.index('mcq_q1'), self.flow.index('profession'))
        self.assertLess(self.flow.index('height'), self.flow.index('marital_status'))
        self.assertLess(self.flow.index('open_1'), self.flow.index('preferences'))
        self.assertGreater(self.flow.index('open_2'), self.flow.index('preferences'))

    def test_financial_question_is_historical_and_inactive(self):
        financial = next(question for question in self.questions['mcq'] if question['id'] == 2)
        self.assertFalse(financial['active'])
        self.assertFalse(financial['matching'])
        self.assertTrue(financial['historical'])

    def test_changed_fields_are_configured_once(self):
        steps = self.questions['onboarding']['steps']
        keys = [step['key'] for step in steps]
        self.assertEqual(keys.count('skin_tone'), 1)
        self.assertEqual(keys.count('body_type'), 1)
        self.assertIn('رياضي', next(step for step in steps if step['key'] == 'body_type')['options'])
        polygyny = next(step for step in steps if step['key'] == 'polygyny_acceptance')
        self.assertEqual(polygyny['show_if'][0]['equals'], 'أنثى')
        preference = next(field for step in steps for field in step.get('fields', []) if field.get('key') == 'nationality_preference')
        self.assertEqual(preference['type'], 'multi_search')

    def test_name_guidance_is_not_brittle(self):
        self.assertEqual(_valid_full_name('عبد الرحمن آل ثاني'), 'عبد الرحمن آل ثاني')
        self.assertEqual(_valid_full_name('ليان أحمد'), 'ليان أحمد')
        self.assertIsNone(_valid_full_name(''))

    def test_nationality_array_and_gender_conditions_are_validated(self):
        normalized, error = _validate_profile_details(self.valid_details, 'ذكر')
        self.assertIsNone(error)
        self.assertEqual(normalized['nationality_preference'], ['قطري', 'سعودي'])

        legacy = {**self.valid_details, 'nationality_preference': 'قطري'}
        normalized, error = _validate_profile_details(legacy, 'ذكر')
        self.assertIsNone(error)
        self.assertEqual(normalized['nationality_preference'], ['قطري'])

        duplicate = {**self.valid_details, 'nationality_preference': ['قطري', 'قطري']}
        self.assertIsNotNone(_validate_profile_details(duplicate, 'ذكر')[1])
        male_only = {**self.valid_details, 'polygyny_acceptance': 'نعم'}
        self.assertIsNotNone(_validate_profile_details(male_only, 'ذكر')[1])
        female = {**self.valid_details, 'marital_status': 'عزباء', 'polygyny_acceptance': 'لا'}
        self.assertIsNone(_validate_profile_details(female, 'أنثى')[1])

    def test_open_answer_lengths_are_validated(self):
        answers = {'q1': 'وصف قصير جداً', 'q2': 'إجابة واضحة', 'q3': 'إجابة واضحة', 'q4': 'إجابة واضحة'}
        self.assertFalse(_validate_open_answers(answers)[0])
        answers['q1'] = 'أنا شخص هادئ وجاد وأقدّر الحوار والمسؤولية الأسرية.'
        self.assertTrue(_validate_open_answers(answers)[0])


if __name__ == '__main__':
    unittest.main()
