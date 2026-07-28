#!/usr/bin/env python3
"""
WEFAQ System Test Suite
========================
Run from the backend folder to verify API flows and security:

    cd backend
    python test_system.py

Uses an isolated temp database and data directory — does not touch production files.
Exit code 0 = all passed, 1 = one or more failures.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_ROOT = tempfile.mkdtemp(prefix='wefaq_test_')
TEST_DATA = os.path.join(TEST_ROOT, 'data')
TEST_INSTANCE = os.path.join(TEST_ROOT, 'instance')
os.makedirs(TEST_DATA)
os.makedirs(TEST_INSTANCE)

# Seed isolated test data before importing the app
shutil.copy(os.path.join(BACKEND_DIR, 'data', 'admins.json'), os.path.join(TEST_DATA, 'admins.json'))
shutil.copy(os.path.join(BACKEND_DIR, 'data', 'questions.json'), os.path.join(TEST_DATA, 'questions.json'))
with open(os.path.join(TEST_DATA, 'users.json'), 'w', encoding='utf-8') as f:
    json.dump([], f)

os.environ['WEFAQ_DATA_DIR'] = TEST_DATA
os.environ['WEFAQ_INSTANCE_DIR'] = TEST_INSTANCE
os.environ['WEFAQ_TESTING'] = '1'
os.environ['WEFAQ_SECRET_KEY'] = 'test-secret-key-not-for-production'

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app  # noqa: E402

app = create_app()
client = app.test_client()

# Shared state populated during tests
state: dict = {}


def _json(method, path, *, headers=None, body=None):
    hdrs = {'Content-Type': 'application/json'}
    if headers:
        hdrs.update(headers)
    kwargs = {'headers': hdrs}
    if body is not None:
        kwargs['json'] = body
    return getattr(client, method.lower())(path, **kwargs)


def admin_headers(admin_id):
    return {'X-Admin-Id': str(admin_id)}


def user_headers(code):
    return {'X-User-Code': code}


def assert_ok(resp, expected_status=200):
    assert resp.status_code == expected_status, (
        f'expected {expected_status}, got {resp.status_code}: {resp.get_data(as_text=True)}'
    )
    data = resp.get_json()
    assert data is not None, 'response is not JSON'
    return data


def assert_fail(resp, expected_status):
    assert resp.status_code == expected_status, (
        f'expected {expected_status}, got {resp.status_code}: {resp.get_data(as_text=True)}'
    )


def sample_personal(name='فاطمة أحمد'):
    return {
        'full_name': name,
        'phone': '0501234567',
        'email': 'fatima.test@example.com',
        'birthday': '1998-05-15',
        'gender': 'أنثى',
        'country': 'السعودية',
        'guardian_phone': '0509876543',
        'guardian_relation': 'أب'
    }


def sample_mcq():
    return {'q1': 'بكالوريوس', 'q2': 'متوسط', 'q3': 'لا', 'q4': 'التدين'}


def sample_open():
    return {
        'q1': 'هادئة مجتهدة',
        'q2': 'شريك متدين',
        'q3': 'أسرة مستقرة',
        'q4': 'لا شروط إضافية'
    }


# ---------------------------------------------------------------------------
# SIMPLE CASES — happy-path flows
# ---------------------------------------------------------------------------

def test_questions_load():
    data = assert_ok(_json('get', '/api/questions'))
    assert data['success'] is True
    assert len(data['questions']['mcq']) == 4
    assert len(data['questions']['open']) == 4


def test_super_admin_login():
    data = assert_ok(_json('post', '/api/auth/admin-login', body={
        'email': 'super@wefaq.com',
        'password': 'SuperAdmin@2026'
    }))
    assert data['admin']['is_super_admin'] is True
    state['super_admin_id'] = data['admin']['id']


def test_admin_login_wrong_password():
    resp = _json('post', '/api/auth/admin-login', body={
        'email': 'super@wefaq.com',
        'password': 'wrong-password'
    })
    assert_fail(resp, 401)


def test_generate_user_code():
    data = assert_ok(_json('post', '/api/admin/users/generate-code',
                           headers=admin_headers(state['super_admin_id']),
                           body={'full_name': ''}), 201)
    state['user_id'] = data['user']['id']
    state['user_code'] = data['user']['code']
    assert data['user']['full_name'] == 'متقدم جديد'


def test_user_login_with_code():
    data = assert_ok(_json('post', '/api/auth/user-login', body={'code': state['user_code']}))
    assert data['user']['needs_onboarding'] is True


def test_complete_application():
    data = assert_ok(_json('post', f"/api/users/{state['user_id']}/complete",
                           headers=user_headers(state['user_code']),
                           body={
                               'personal': sample_personal(),
                               'mcq': sample_mcq(),
                               'open': sample_open()
                           }))
    assert data['user']['needs_onboarding'] is False
    assert data['user']['status'] == 'reviewing'


def test_get_user_profile_as_owner():
    data = assert_ok(_json('get', f"/api/users/{state['user_id']}",
                           headers=user_headers(state['user_code'])))
    assert data['user']['full_name'] == 'فاطمة أحمد'
    assert data['mcq_answers']['q1'] == 'بكالوريوس'


def test_admin_list_users():
    data = assert_ok(_json('get', '/api/admin/users',
                           headers=admin_headers(state['super_admin_id'])))
    assert data['count'] >= 1


def test_admin_update_status_creates_notification():
    assert_ok(_json('put', f"/api/admin/users/{state['user_id']}/status",
                    headers=admin_headers(state['super_admin_id']),
                    body={'status': 'approved', 'status_reason': 'مطابق للمعايير'}))

    notif = assert_ok(_json('get', f"/api/notifications/user/{state['user_id']}",
                            headers=user_headers(state['user_code'])))
    assert len(notif['notifications']) >= 1


def test_visible_note_shown_to_user():
    assert_ok(_json('post', f"/api/admin/users/{state['user_id']}/notes",
                    headers=admin_headers(state['super_admin_id']),
                    body={
                        'note_text': 'ملاحظة مرئية للمتقدم',
                        'is_visible_to_user': True
                    }), 201)

    assert_ok(_json('post', f"/api/admin/users/{state['user_id']}/notes",
                    headers=admin_headers(state['super_admin_id']),
                    body={
                        'note_text': 'ملاحظة داخلية سرية',
                        'is_visible_to_user': False
                    }), 201)

    profile = assert_ok(_json('get', f"/api/users/{state['user_id']}",
                              headers=user_headers(state['user_code'])))
    visible_texts = [n['note_text'] for n in profile['visible_notes']]
    assert 'ملاحظة مرئية للمتقدم' in visible_texts
    assert 'ملاحظة داخلية سرية' not in visible_texts


def test_user_update_profile():
    data = assert_ok(_json('put', f"/api/users/{state['user_id']}",
                           headers=user_headers(state['user_code']),
                           body={'phone': '0551112233'}))
    assert data['user']['phone'] == '0551112233'


# ---------------------------------------------------------------------------
# HARD CASES — security, edge cases, validation
# ---------------------------------------------------------------------------

def test_idor_get_user_without_auth():
    resp = _json('get', f"/api/users/{state['user_id']}")
    assert_fail(resp, 403)


def test_idor_get_user_wrong_code():
    resp = _json('get', f"/api/users/{state['user_id']}",
                 headers=user_headers('USER999'))
    assert_fail(resp, 403)


def test_idor_update_other_user():
    gen = assert_ok(_json('post', '/api/admin/users/generate-code',
                          headers=admin_headers(state['super_admin_id']),
                          body={'full_name': 'متقدم آخر'}), 201)
    other_id = gen['user']['id']
    resp = _json('put', f'/api/users/{other_id}',
                 headers=user_headers(state['user_code']),
                 body={'phone': '0500000000'})
    assert_fail(resp, 403)


def test_admin_routes_without_auth():
    resp = _json('get', '/api/admin/users')
    assert_fail(resp, 403)

    resp = _json('post', '/api/admin/users/generate-code', body={'full_name': 'هاكر'})
    assert_fail(resp, 403)


def test_create_admin_without_super_admin():
    # Create a regular admin first (as super admin)
    create = assert_ok(_json('post', '/api/admin/create',
                             headers=admin_headers(state['super_admin_id']),
                             body={
                                 'full_name': 'إداري تجريبي',
                                 'phone': '0500000001',
                                 'email': 'regular.admin@test.com',
                                 'city': 'الرياض',
                                 'password': 'RegularAdmin1'
                             }), 201)
    state['regular_admin_id'] = create['admin_id']

    resp = _json('post', '/api/admin/create',
                 headers=admin_headers(state['regular_admin_id']),
                 body={
                     'full_name': 'إداري غير مصرح',
                     'phone': '0500000002',
                     'email': 'hacker@test.com',
                     'city': 'الرياض',
                     'password': 'HackerPass1'
                 })
    assert_fail(resp, 403)


def test_create_admin_weak_password():
    resp = _json('post', '/api/admin/create',
                 headers=admin_headers(state['super_admin_id']),
                 body={
                     'full_name': 'ضعيف',
                     'phone': '0500000003',
                     'email': 'weak@test.com',
                     'city': 'الرياض',
                     'password': '123'
                 })
    assert_fail(resp, 400)


def test_delete_super_admin_blocked():
    resp = _json('delete', f"/api/admin/admins/{state['super_admin_id']}",
                 headers=admin_headers(state['super_admin_id']),
                 body={'admin_id': state['super_admin_id']})
    assert_fail(resp, 400)


def test_placeholder_name_rejected_on_complete():
    gen = assert_ok(_json('post', '/api/admin/users/generate-code',
                          headers=admin_headers(state['super_admin_id']),
                          body={'full_name': ''}), 201)
    uid, code = gen['user']['id'], gen['user']['code']
    personal = sample_personal()
    personal['full_name'] = 'متقدم جديد'
    personal['email'] = 'placeholder@test.com'
    resp = _json('post', f'/api/users/{uid}/complete',
                 headers=user_headers(code),
                 body={'personal': personal, 'mcq': sample_mcq(), 'open': sample_open()})
    assert_fail(resp, 400)


def test_invalid_status_rejected():
    resp = _json('put', f"/api/admin/users/{state['user_id']}/status",
                 headers=admin_headers(state['super_admin_id']),
                 body={'status': 'hacked'})
    assert_fail(resp, 400)


def test_invalid_birthday_rejected():
    gen = assert_ok(_json('post', '/api/admin/users/generate-code',
                          headers=admin_headers(state['super_admin_id']),
                          body={'full_name': ''}), 201)
    uid, code = gen['user']['id'], gen['user']['code']
    personal = sample_personal()
    personal['birthday'] = 'not-a-date'
    personal['email'] = 'badbirthday@test.com'
    resp = _json('post', f'/api/users/{uid}/complete',
                 headers=user_headers(code),
                 body={'personal': personal, 'mcq': sample_mcq(), 'open': sample_open()})
    assert_fail(resp, 400)


def test_incomplete_mcq_rejected():
    gen = assert_ok(_json('post', '/api/admin/users/generate-code',
                          headers=admin_headers(state['super_admin_id']),
                          body={'full_name': ''}), 201)
    uid, code = gen['user']['id'], gen['user']['code']
    personal = sample_personal()
    personal['email'] = 'incomplete@test.com'
    resp = _json('post', f'/api/users/{uid}/complete',
                 headers=user_headers(code),
                 body={'personal': personal, 'mcq': {'q1': 'بكالوريوس'}, 'open': sample_open()})
    assert_fail(resp, 400)


def test_user_code_generation_after_delete_no_crash():
    """Deleting a user then generating a new code must not cause a 500/409 collision."""
    gen1 = assert_ok(_json('post', '/api/admin/users/generate-code',
                           headers=admin_headers(state['super_admin_id']),
                           body={'full_name': 'للحذف'}), 201)
    uid1 = gen1['user']['id']

    assert_ok(_json('delete', f'/api/admin/users/{uid1}',
                    headers=admin_headers(state['super_admin_id']),
                    body={'admin_id': state['super_admin_id']}))

    gen2 = assert_ok(_json('post', '/api/admin/users/generate-code',
                           headers=admin_headers(state['super_admin_id']),
                           body={'full_name': 'بعد الحذف'}), 201)
    assert gen2['user']['code'].startswith('USER')


def test_register_without_admin_auth():
    resp = _json('post', '/api/users/register', body=sample_personal('مسجل بدون إذن'))
    assert_fail(resp, 403)


def test_notifications_without_auth():
    resp = _json('get', f"/api/notifications/user/{state['user_id']}")
    assert_fail(resp, 403)


def test_mark_notification_without_auth():
    notif = assert_ok(_json('get', f"/api/notifications/user/{state['user_id']}",
                            headers=user_headers(state['user_code'])))
    nid = notif['notifications'][0]['id']
    resp = _json('put', f'/api/notifications/{nid}/read')
    assert_fail(resp, 403)


def test_invalid_user_login_code():
    resp = _json('post', '/api/auth/user-login', body={'code': 'INVALIDCODE'})
    assert_fail(resp, 404)


def test_invalid_email_rejected():
    gen = assert_ok(_json('post', '/api/admin/users/generate-code',
                          headers=admin_headers(state['super_admin_id']),
                          body={'full_name': ''}), 201)
    uid, code = gen['user']['id'], gen['user']['code']
    personal = sample_personal()
    personal['email'] = 'not-an-email'
    resp = _json('post', f'/api/users/{uid}/complete',
                 headers=user_headers(code),
                 body={'personal': personal, 'mcq': sample_mcq(), 'open': sample_open()})
    assert_fail(resp, 400)


def test_sql_injection_in_name_stored_safely():
    gen = assert_ok(_json('post', '/api/admin/users/generate-code',
                          headers=admin_headers(state['super_admin_id']),
                          body={'full_name': ''}), 201)
    uid, code = gen['user']['id'], gen['user']['code']
    personal = sample_personal("'; DROP TABLE users; --")
    personal['email'] = 'sqlinj@test.com'
    data = assert_ok(_json('post', f'/api/users/{uid}/complete',
                           headers=user_headers(code),
                           body={'personal': personal, 'mcq': sample_mcq(), 'open': sample_open()}))
    assert "DROP TABLE" in data['user']['full_name']
    # DB still works — list users succeeds
    assert_ok(_json('get', '/api/admin/users', headers=admin_headers(state['super_admin_id'])))


def test_admin_read_user_via_admin_header():
    data = assert_ok(_json('get', f"/api/users/{state['user_id']}",
                           headers=admin_headers(state['super_admin_id'])))
    assert data['user']['id'] == state['user_id']


def test_list_admins_super_admin_only():
    resp = _json('get', '/api/admin/admins',
                 headers=admin_headers(state['regular_admin_id']))
    assert_fail(resp, 403)

    data = assert_ok(_json('get', '/api/admin/admins',
                           headers=admin_headers(state['super_admin_id'])))
    assert any(a['is_super_admin'] for a in data['admins'])


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

SIMPLE_TESTS = [
    test_questions_load,
    test_super_admin_login,
    test_admin_login_wrong_password,
    test_generate_user_code,
    test_user_login_with_code,
    test_complete_application,
    test_get_user_profile_as_owner,
    test_admin_list_users,
    test_admin_update_status_creates_notification,
    test_visible_note_shown_to_user,
    test_user_update_profile,
]

HARD_TESTS = [
    test_idor_get_user_without_auth,
    test_idor_get_user_wrong_code,
    test_idor_update_other_user,
    test_admin_routes_without_auth,
    test_create_admin_without_super_admin,
    test_create_admin_weak_password,
    test_delete_super_admin_blocked,
    test_placeholder_name_rejected_on_complete,
    test_invalid_status_rejected,
    test_invalid_birthday_rejected,
    test_incomplete_mcq_rejected,
    test_user_code_generation_after_delete_no_crash,
    test_register_without_admin_auth,
    test_notifications_without_auth,
    test_mark_notification_without_auth,
    test_invalid_user_login_code,
    test_invalid_email_rejected,
    test_sql_injection_in_name_stored_safely,
    test_admin_read_user_via_admin_header,
    test_list_admins_super_admin_only,
]


def run_suite(label, tests):
    passed = failed = 0
    print(f'\n{"=" * 60}')
    print(f'  {label}')
    print('=' * 60)
    for test_fn in tests:
        name = test_fn.__name__
        try:
            test_fn()
            print(f'  ✓ PASS  {name}')
            passed += 1
        except AssertionError as exc:
            print(f'  ✗ FAIL  {name}: {exc}')
            failed += 1
        except Exception as exc:
            print(f'  ✗ ERROR {name}: {type(exc).__name__}: {exc}')
            failed += 1
    return passed, failed


def main():
    print('WEFAQ System Test Suite')
    print(f'Isolated test dir: {TEST_ROOT}')

    total_pass = total_fail = 0
    for label, group in [('SIMPLE CASES (happy path)', SIMPLE_TESTS),
                         ('HARD CASES (security & edge)', HARD_TESTS)]:
        p, f = run_suite(label, group)
        total_pass += p
        total_fail += f

    print(f'\n{"=" * 60}')
    print(f'  RESULT: {total_pass} passed, {total_fail} failed')
    print('=' * 60)

    shutil.rmtree(TEST_ROOT, ignore_errors=True)
    return 0 if total_fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
