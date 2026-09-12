"""Focused tests for the deterministic matching engine (no database required)."""
import os
import sys
import unittest
from datetime import date
from types import SimpleNamespace

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ['WEFAQ_DATA_DIR'] = os.path.join(BACKEND_DIR, 'models', 'data')
sys.path.insert(0, BACKEND_DIR)

from services.matching_service import (  # noqa: E402
    _candidate_summary,
    find_matches_for_user,
    matching_factors,
    score_factor,
    score_multi_select,
    score_pair,
)
from app import create_app  # noqa: E402
from models import Admin, MCQAnswer, OpenAnswer, User, UserProfile, db  # noqa: E402


def candidate(identifier, gender, *, age=30, status='approved', details=None, mcq=None, open_text='نبذة محترمة'):
    birthday = date(date.today().year - age, 1, 1)
    profile = SimpleNamespace(details={
        'nationality': 'قطري', 'profession': 'مهندس', 'marital_status': 'لم أتزوج من قبل',
        'marriage_timeline': '3 أشهر', 'height': 175, 'weight': 75,
        'age_min': 24, 'age_max': 35, 'height_min': 165, 'height_max': 185,
        'marital_preference': 'لا يهم', 'nationality_preference': 'لا يهم', **(details or {}),
    })
    answers = {'q1': 'بكالوريوس', 'q2': 'متوسط', 'q3': 'ليس مهماً', 'q4': 'الأخلاق', **(mcq or {})}
    return SimpleNamespace(id=identifier, code=f'USER{identifier:03d}', full_name=f'مرشح {identifier}', phone='50000000',
                           email='private@example.com', guardian_phone='51111111', birthday=birthday, gender=gender,
                           country='قطر', status=status, profile=profile,
                           mcq_answers=SimpleNamespace(answers=answers, q1=answers['q1'], q2=answers['q2'], q3=answers['q3'], q4=answers['q4']),
                           open_answers=SimpleNamespace(q1=open_text))


class MatchingServiceTests(unittest.TestCase):
    def setUp(self):
        self.a = candidate(1, 'ذكر', age=30)
        self.b = candidate(2, 'أنثى', age=28)

    def test_current_configuration_discovers_all_active_factors(self):
        self.assertEqual(len(matching_factors()), 8)

    def test_identical_answers_are_high(self):
        self.assertGreaterEqual(score_pair(self.a, self.b)['compatibility_percentage'], 90)

    def test_adjacent_ordinal_beats_distant(self):
        factor = {'matching_method': 'ordinal', 'matching_order': ['أ', 'ب', 'ج', 'د', 'هـ']}
        adjacent = score_factor(candidate(3, 'ذكر', details={'x': 'د'}), candidate(4, 'أنثى', details={'x': 'ج'}), {**factor, 'source': 'profile', 'answer_key': 'x'})[0]
        distant = score_factor(candidate(5, 'ذكر', details={'x': 'هـ'}), candidate(6, 'أنثى', details={'x': 'أ'}), {**factor, 'source': 'profile', 'answer_key': 'x'})[0]
        self.assertGreater(adjacent, distant)
        self.assertEqual(distant, 0)

    def test_age_inside_range_is_full(self):
        age = next(f for f in matching_factors() if f['key'] == 'age_preference')
        self.assertEqual(score_factor(self.a, self.b, age)[0], 100)

    def test_age_tolerance_gradually_reduces_then_reaches_zero(self):
        age = next(f for f in matching_factors() if f['key'] == 'age_preference')
        near = candidate(3, 'أنثى', age=36, details={'age_min': 24, 'age_max': 35})
        far = candidate(4, 'أنثى', age=45, details={'age_min': 24, 'age_max': 35})
        self.assertGreater(score_factor(self.a, near, age)[0], score_factor(self.a, far, age)[0])
        self.assertEqual(score_factor(self.a, far, age)[0], 50)  # reverse direction is still satisfied

    def test_bidirectional_age_is_one_factor(self):
        result = score_pair(self.a, self.b)
        self.assertIn('age_preference', result['breakdown'])
        self.assertEqual(len(result['breakdown']['age_preference']['directional_scores']), 2)
        self.assertEqual(result['applicable_factors'], 8)

    def test_multiselect_uses_normalized_overlap(self):
        self.assertGreater(score_multi_select(['قراءة', 'سفر'], ['قراءة', 'سفر', 'تطوع'], {}), score_multi_select(['قراءة'], ['رياضة'], {}))

    def test_missing_values_are_skipped_not_matched(self):
        factor = {'key': 'missing', 'source': 'profile', 'answer_key': 'unknown', 'matching_method': 'exact'}
        result = score_pair(self.a, self.b, factors=[factor])
        self.assertFalse(result['has_sufficient_data'])
        self.assertEqual(result['skipped_factors'], ['missing'])

    def test_non_applicable_conditional_data_does_not_reduce_score(self):
        factor = {'key': 'children', 'source': 'profile', 'answer_key': 'kids_count', 'matching_method': 'numeric', 'matching_tolerance': 3}
        self.assertEqual(score_pair(self.a, self.b, factors=[factor])['compatibility_percentage'], 0)
        self.assertFalse(score_pair(self.a, self.b, factors=[factor])['has_sufficient_data'])

    def test_eligibility_does_not_add_points(self):
        result = score_pair(self.a, self.b, factors=[])
        self.assertTrue(result['eligible'])
        self.assertEqual(result['compatibility_percentage'], 0)

    def test_same_gender_is_ineligible_without_changing_factor_score(self):
        other = candidate(3, 'ذكر')
        result = score_pair(self.a, other)
        self.assertFalse(result['eligible'])
        self.assertGreater(result['compatibility_percentage'], 0)

    def test_open_answers_never_change_score(self):
        before = score_pair(self.a, self.b)['compatibility_percentage']
        self.b.open_answers.q1 = 'نص مختلف تماماً'
        self.assertEqual(score_pair(self.a, self.b)['compatibility_percentage'], before)

    def test_weight_similarity_is_not_a_factor(self):
        before = score_pair(self.a, self.b)['compatibility_percentage']
        self.b.profile.details['weight'] = 150
        self.assertEqual(score_pair(self.a, self.b)['compatibility_percentage'], before)

    def test_height_preference_compares_against_actual_height(self):
        factor = next(f for f in matching_factors() if f['key'] == 'height_preference')
        self.b.profile.details['height'] = 220
        score, directions = score_factor(self.a, self.b, factor)
        self.assertEqual(directions[0], 0)
        self.assertEqual(score, 50)

    def test_new_configured_factor_needs_no_engine_change(self):
        custom = {'key': 'profession', 'source': 'profile', 'answer_key': 'profession', 'matching_method': 'exact'}
        self.assertEqual(score_pair(self.a, self.b, factors=[custom])['compatibility_percentage'], 100)

    def test_score_is_bounded_and_no_division_by_zero(self):
        self.assertEqual(score_pair(self.a, self.b, factors=[])['compatibility_percentage'], 0)
        factor = {'key': 'matrix', 'source': 'profile', 'answer_key': 'profession', 'matching_method': 'matrix',
                  'matching_matrix': {'مهندس': {'مهندس': 500}}}
        self.assertEqual(score_pair(self.a, self.b, factors=[factor])['compatibility_percentage'], 100)

    def test_ranking_is_descending_and_ties_are_stable_by_id(self):
        low = candidate(4, 'أنثى', mcq={'q4': 'المظهر'}, details={'age_min': 60, 'age_max': 70})
        high_later = candidate(3, 'أنثى')
        high_first = candidate(2, 'أنثى')
        results = find_matches_for_user(self.a, [low, high_later, high_first], allowed_statuses=('approved',))
        self.assertEqual([item['candidate']['id'] for item in results[:2]], [2, 3])
        self.assertGreaterEqual(results[1]['compatibility_percentage'], results[2]['compatibility_percentage'])

    def test_duplicates_are_removed_and_limit_is_respected(self):
        results = find_matches_for_user(self.a, [self.b, self.b], limit=1, allowed_statuses=('approved',))
        self.assertEqual(len(results), 1)

    def test_unapproved_candidate_is_filtered(self):
        reviewing = candidate(3, 'أنثى', status='reviewing')
        self.assertEqual(find_matches_for_user(self.a, [reviewing], allowed_statuses=('approved',)), [])

    def test_public_summary_excludes_private_identifiers_and_contacts(self):
        result = find_matches_for_user(self.a, [self.b], private=True, allowed_statuses=('approved',))[0]
        for secret in ('full_name', 'phone', 'email', 'guardian_phone', 'code', 'birthday', 'id'):
            self.assertNotIn(secret, result['candidate'])
        self.assertNotIn('breakdown', result)
        self.assertIn('profile_description', result['candidate'])

    def test_admin_summary_keeps_only_expected_supervisor_identity(self):
        summary = _candidate_summary(self.b)
        self.assertIn('id', summary)
        self.assertIn('full_name', summary)
        self.assertNotIn('phone', summary)
        self.assertNotIn('email', summary)


class MatchingApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            db.drop_all()
            db.create_all()
            admin = Admin(full_name='مشرف الاختبار', phone='50000000', email='admin@tests.local', city='الدوحة',
                          password_hash='unused', is_super_admin=True, is_active=True)
            male = User(code='USER901', full_name='اسم خاص أول', birthday=date(1995, 1, 1), gender='ذكر', country='قطر', status='approved')
            female = User(code='USER902', full_name='اسم خاص ثان', birthday=date(1998, 1, 1), gender='أنثى', country='قطر', status='approved')
            db.session.add_all([admin, male, female])
            db.session.flush()
            for user in (male, female):
                db.session.add(UserProfile(user_id=user.id, details={
                    'nationality': 'قطري', 'profession': 'مهندس', 'marital_status': 'لم أتزوج من قبل',
                    'marriage_timeline': '3 أشهر', 'height': 175, 'weight': 75,
                    'age_min': 24, 'age_max': 40, 'height_min': 160, 'height_max': 190,
                    'marital_preference': 'لا يهم', 'nationality_preference': 'لا يهم'}))
                db.session.add(MCQAnswer(user_id=user.id, answers={'q1': 'بكالوريوس', 'q2': 'متوسط', 'q3': 'ليس مهماً', 'q4': 'الأخلاق'}))
                db.session.add(OpenAnswer(user_id=user.id, q1='نبذة آمنة', q2='إجابة', q3='إجابة', q4='إجابة'))
            db.session.commit()
            cls.admin_id, cls.male_id, cls.female_id = admin.id, male.id, female.id

    def test_public_endpoint_is_privacy_safe(self):
        response = self.client.get(f'/api/admin/public/users/{self.male_id}/matches', headers={'X-User-Code': 'USER901'})
        self.assertEqual(response.status_code, 200)
        match = response.get_json()['matches'][0]
        self.assertNotIn('breakdown', match)
        for key in ('id', 'full_name', 'phone', 'email', 'code', 'birthday'):
            self.assertNotIn(key, match['candidate'])

    def test_admin_endpoint_returns_explainable_breakdown(self):
        response = self.client.get(f'/api/admin/users/{self.male_id}/matches', headers={'X-Admin-Id': str(self.admin_id)})
        self.assertEqual(response.status_code, 200)
        match = response.get_json()['matches'][0]
        self.assertEqual(match['applicable_factors'], 8)
        self.assertIn('age_preference', match['breakdown'])

    def test_pair_endpoint_keeps_eligibility_separate(self):
        response = self.client.get(f'/api/admin/matches/pair?user_a={self.male_id}&user_b={self.female_id}',
                                   headers={'X-Admin-Id': str(self.admin_id)})
        self.assertEqual(response.status_code, 200)
        match = response.get_json()['match']
        self.assertTrue(match['eligibility']['eligible'])
        self.assertNotIn('eligibility', match['breakdown'])


if __name__ == '__main__':
    unittest.main()
