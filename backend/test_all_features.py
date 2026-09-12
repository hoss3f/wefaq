#!/usr/bin/env python3
"""
WEFAQ — Full Feature Test Suite
===============================
Exercises every backend feature: auth, onboarding, user lifecycle, admin
management, notes, assignment, activity logs, notifications, the matching
engine, matching endpoints, candidate interactions, uploads and the
validation/utility layer.

    cd backend
    python test_all_features.py

Runs against an isolated temp database and data directory — never touches
development or production data.  Exit code 0 = all passed, 1 = failures.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import traceback
from datetime import date, timedelta

# Windows consoles default to cp1252 and cannot print the Arabic/✓✗ output.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_ROOT = tempfile.mkdtemp(prefix='wefaq_features_')
TEST_DATA = os.path.join(TEST_ROOT, 'data')
TEST_INSTANCE = os.path.join(TEST_ROOT, 'instance')
TEST_UPLOADS = os.path.join(TEST_ROOT, 'uploads')
for _path in (TEST_DATA, TEST_INSTANCE, TEST_UPLOADS):
    os.makedirs(_path, exist_ok=True)

shutil.copy(os.path.join(BACKEND_DIR, 'models', 'data', 'admins.json'), os.path.join(TEST_DATA, 'admins.json'))
shutil.copy(os.path.join(BACKEND_DIR, 'models', 'data', 'questions.json'), os.path.join(TEST_DATA, 'questions.json'))
with open(os.path.join(TEST_DATA, 'users.json'), 'w', encoding='utf-8') as handle:
    json.dump([], handle)

os.environ['WEFAQ_DATA_DIR'] = TEST_DATA
os.environ['WEFAQ_INSTANCE_DIR'] = TEST_INSTANCE
os.environ['WEFAQ_UPLOAD_DIR'] = TEST_UPLOADS
os.environ['WEFAQ_TESTING'] = '1'
os.environ['WEFAQ_SEED_DEMO'] = '0'
os.environ['DATABASE_URL'] = f"sqlite:///{os.path.join(TEST_INSTANCE, 'features.db')}"
# No SMTP configuration -> the welcome mail is skipped instead of dialling out.
for _smtp_key in ('SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_FROM'):
    os.environ.pop(_smtp_key, None)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app  # noqa: E402
from models import Admin, MCQAnswer, Notification, db  # noqa: E402
from security import sanitize_text, validate_birthday, validate_email, validate_text_answer  # noqa: E402
from services.matching_service import (  # noqa: E402
    compute_age,
    evaluate_eligibility,
    matching_factors,
    score_boolean,
    score_multi_select,
    score_numeric,
    score_ordinal,
)
from utils import (  # noqa: E402
    hash_password,
    is_placeholder_name,
    load_questions,
    photo_url_for,
    read_json_file,
    verify_password,
)

app = create_app()
client = app.test_client()
state: dict = {}

QUESTIONS = load_questions()
MATCHING_MCQ_KEYS = [
    question.get('answer_key') or f"q{question['id']}"
    for question in QUESTIONS['mcq'] if question.get('matching')
]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def call(method, path, *, headers=None, body=None):
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


def expect(resp, status=200):
    """Assert the status code and return the decoded JSON body."""
    body = resp.get_data(as_text=True)
    assert resp.status_code == status, f'expected HTTP {status}, got {resp.status_code}: {body[:400]}'
    data = resp.get_json()
    assert data is not None, f'response was not JSON: {body[:200]}'
    return data


def sample_personal(name='نور الهدى', gender='أنثى', birthday='1998-05-15', email=None, **overrides):
    payload = {
        'full_name': name,
        'birthday': birthday,
        'gender': gender,
        'country': 'قطر',
        'phone': '0500000000',
        'email': email or 'candidate@example.com',
        'guardian_phone': '0511111111',
        'guardian_relation': 'الأب',
        'profile_details': {
            'nationality': 'قطري',
            'profession': 'مهندسة',
            'marital_status': 'لم أتزوج من قبل',
            'marriage_timeline': '3 أشهر',
            'height': 165,
            'weight': 60,
            'age_min': 24, 'age_max': 40,
            'height_min': 160, 'height_max': 195,
            'marital_preference': 'لا يهم',
            'nationality_preference': 'لا يهم',
        },
    }
    payload['profile_details'].update(overrides.pop('profile_details', {}))
    payload.update(overrides)
    return payload


def sample_mcq(**overrides):
    answers = {'q1': 'بكالوريوس', 'q2': 'متوسط', 'q3': 'لا', 'q4': 'التدين'}
    answers.update(overrides)
    for key in MATCHING_MCQ_KEYS:
        answers.setdefault(key, 'بكالوريوس')
    return answers


def sample_open(**overrides):
    answers = {
        'q1': 'شخصية هادئة تحب القراءة والعمل التطوعي',
        'q2': 'أبحث عن شريك متدين وصاحب خلق',
        'q3': 'أسرة مستقرة ومتوسطة الحال',
        'q4': 'لا توجد شروط إضافية',
    }
    answers.update(overrides)
    return answers


def make_candidate(name, gender, birthday, *, approve=True, mcq=None):
    """Generate a code, complete the application, and optionally approve it."""
    gen = expect(call('post', '/api/admin/users/generate-code',
                      headers=admin_headers(state['super_admin_id']),
                      body={'full_name': name, 'admin_id': state['super_admin_id']}), 201)
    uid, code = gen['user']['id'], gen['user']['code']
    personal = sample_personal(name, gender, birthday, email=f'{code.lower()}@example.com')
    expect(call('post', f'/api/users/{uid}/complete', headers=user_headers(code),
                body={'personal': personal, 'mcq': sample_mcq(**(mcq or {})), 'open': sample_open()}))
    if approve:
        expect(call('put', f'/api/admin/users/{uid}/status',
                    headers=admin_headers(state['super_admin_id']),
                    body={'status': 'approved', 'admin_id': state['super_admin_id']}))
    return uid, code


# ==========================================================================
# 1. AUTHENTICATION
# ==========================================================================
def test_admin_login_success():
    super_admin = read_json_file('admins.json')['super_admin']
    data = expect(call('post', '/api/auth/admin-login',
                       body={'email': super_admin['email'], 'password': super_admin['password']}))
    assert data['admin']['is_super_admin'] is True
    state['super_admin_id'] = data['admin']['id']
    state['super_admin_email'] = super_admin['email']
    state['super_admin_password'] = super_admin['password']


def test_admin_login_is_case_insensitive():
    data = expect(call('post', '/api/auth/admin-login',
                       body={'email': state['super_admin_email'].upper(),
                             'password': state['super_admin_password']}))
    assert data['admin']['id'] == state['super_admin_id']


def test_admin_login_wrong_password_rejected():
    expect(call('post', '/api/auth/admin-login',
                body={'email': state['super_admin_email'], 'password': 'wrong-password'}), 401)


def test_admin_login_missing_fields_rejected():
    expect(call('post', '/api/auth/admin-login', body={'email': '', 'password': ''}), 400)
    expect(call('post', '/api/auth/admin-login', body={}), 400)


def test_inactive_admin_cannot_login():
    with app.app_context():
        admin = Admin(full_name='معطّل', phone='0500000099', email='inactive@test.com',
                      city='الدوحة', password_hash=hash_password('InactivePass1'),
                      is_super_admin=False, is_active=False)
        db.session.add(admin)
        db.session.commit()
        state['inactive_admin_id'] = admin.id
    expect(call('post', '/api/auth/admin-login',
                body={'email': 'inactive@test.com', 'password': 'InactivePass1'}), 403)


def test_user_login_flow():
    gen = expect(call('post', '/api/admin/users/generate-code',
                      headers=admin_headers(state['super_admin_id']),
                      body={'full_name': 'فاطمة أحمد', 'admin_id': state['super_admin_id']}), 201)
    state['user_id'], state['user_code'] = gen['user']['id'], gen['user']['code']
    data = expect(call('post', '/api/auth/user-login', body={'code': state['user_code']}))
    assert data['user']['needs_onboarding'] is True, 'a fresh code must require onboarding'
    assert data['user']['status'] == 'pending'


def test_user_login_bad_code_rejected():
    expect(call('post', '/api/auth/user-login', body={'code': ''}), 400)
    expect(call('post', '/api/auth/user-login', body={'code': 'NOPE999'}), 404)


# ==========================================================================
# 2. QUESTIONS / ONBOARDING CONFIG
# ==========================================================================
def test_questions_endpoint_matches_configuration():
    data = expect(call('get', '/api/questions'))
    assert data['questions']['mcq'] == QUESTIONS['mcq'], 'endpoint must serve questions.json verbatim'
    assert len(data['questions']['open']) == len(QUESTIONS['open'])
    assert 'onboarding' in data['questions'], 'onboarding steps must reach the frontend'


def test_every_matching_question_is_well_formed():
    """Any question flagged for matching must carry the config its scorer needs."""
    required_by_method = {
        'ordinal': ['matching_order'],
        'matrix': ['matching_matrix'],
        'pair_preference': ['matching_relation_key', 'matching_relation_scores'],
        'preference_range': ['min_key', 'max_key', 'matching_actual_key'],
        'preference_exact': ['matching_actual_key'],
    }
    problems = []
    for factor in matching_factors():
        if not factor.get('key'):
            problems.append(f'factor without key: {factor.get("label")}')
        for field in required_by_method.get(factor.get('matching_method', 'exact'), []):
            if not factor.get(field):
                problems.append(f'{factor.get("key")}: missing {field}')
    assert not problems, '; '.join(problems)


# ==========================================================================
# 3. USER LIFECYCLE
# ==========================================================================
def test_complete_application():
    personal = sample_personal('فاطمة أحمد', email='fatima@example.com')
    data = expect(call('post', f"/api/users/{state['user_id']}/complete",
                       headers=user_headers(state['user_code']),
                       body={'personal': personal, 'mcq': sample_mcq(), 'open': sample_open()}))
    assert data['user']['status'] == 'reviewing'
    assert data['user']['needs_onboarding'] is False
    assert data['profile_details']['nationality'] == 'قطري'


def test_completed_user_no_longer_needs_onboarding():
    data = expect(call('post', '/api/auth/user-login', body={'code': state['user_code']}))
    assert data['user']['needs_onboarding'] is False


def test_complete_rejects_incomplete_mcq():
    partial = sample_mcq()
    partial.pop(MATCHING_MCQ_KEYS[0])
    resp = call('post', f"/api/users/{state['user_id']}/complete",
                headers=user_headers(state['user_code']),
                body={'personal': sample_personal('فاطمة أحمد'), 'mcq': partial, 'open': sample_open()})
    data = expect(resp, 400)
    assert MATCHING_MCQ_KEYS[0] in data.get('missing_fields', [])


def test_complete_rejects_missing_open_answers():
    resp = call('post', f"/api/users/{state['user_id']}/complete",
                headers=user_headers(state['user_code']),
                body={'personal': sample_personal('فاطمة أحمد'), 'mcq': sample_mcq(),
                      'open': {'q1': 'نص كافٍ', 'q2': 'نص كافٍ', 'q3': 'نص كافٍ'}})
    expect(resp, 400)


def test_complete_rejects_missing_profile_details():
    personal = sample_personal('فاطمة أحمد')
    personal['profile_details'].pop('height')
    resp = call('post', f"/api/users/{state['user_id']}/complete",
                headers=user_headers(state['user_code']),
                body={'personal': personal, 'mcq': sample_mcq(), 'open': sample_open()})
    data = expect(resp, 400)
    assert 'height' in data.get('missing_fields', [])


def test_complete_rejects_placeholder_name():
    resp = call('post', f"/api/users/{state['user_id']}/complete",
                headers=user_headers(state['user_code']),
                body={'personal': sample_personal('متقدم جديد'), 'mcq': sample_mcq(),
                      'open': sample_open()})
    expect(resp, 400)


def test_complete_rejects_underage_and_future_birthdays():
    for bad in ((date.today() + timedelta(days=1)).isoformat(),
                (date.today() - timedelta(days=365 * 10)).isoformat(),
                'not-a-date'):
        resp = call('post', f"/api/users/{state['user_id']}/complete",
                    headers=user_headers(state['user_code']),
                    body={'personal': sample_personal('فاطمة أحمد', birthday=bad),
                          'mcq': sample_mcq(), 'open': sample_open()})
        expect(resp, 400)


def test_get_own_profile():
    data = expect(call('get', f"/api/users/{state['user_id']}",
                       headers=user_headers(state['user_code'])))
    assert data['user']['code'] == state['user_code']
    assert data['open_answers']['q1']
    assert data['profile_details']['profession'] == 'مهندسة'


def test_update_own_profile():
    data = expect(call('put', f"/api/users/{state['user_id']}",
                       headers=user_headers(state['user_code']),
                       body={'phone': '0522222222', 'guardian_relation': 'الأخ'}))
    assert data['user']['phone'] == '0522222222'
    assert data['user']['guardian_relation'] == 'الأخ'


def test_update_rejects_placeholder_name_and_bad_birthday():
    expect(call('put', f"/api/users/{state['user_id']}",
                headers=user_headers(state['user_code']),
                body={'full_name': 'متقدم جديد'}), 400)
    expect(call('put', f"/api/users/{state['user_id']}",
                headers=user_headers(state['user_code']),
                body={'birthday': '15-05-1998'}), 400)


def test_save_answers_endpoint():
    uid, code = make_candidate('سارة العلي', 'أنثى', '1996-02-02', approve=False)
    expect(call('post', f'/api/users/{uid}/answers', headers=user_headers(code),
                body={'mcq': sample_mcq(q4='الأخلاق'), 'open': sample_open(q1='نبذة محدثة عن شخصيتي')}))
    profile = expect(call('get', f'/api/users/{uid}', headers=user_headers(code)))
    assert profile['open_answers']['q1'] == 'نبذة محدثة عن شخصيتي'
    assert profile['user']['status'] == 'reviewing'


def test_unknown_user_returns_404():
    expect(call('get', '/api/users/999999', headers=admin_headers(state['super_admin_id'])), 404)
    expect(call('post', '/api/users/999999/complete', headers=user_headers(state['user_code']),
                body={'personal': sample_personal(), 'mcq': sample_mcq(), 'open': sample_open()}), 404)


# ==========================================================================
# 4. ADMIN — users, status, notes, assignment, logs
# ==========================================================================
def test_admin_lists_users():
    data = expect(call('get', '/api/admin/users', headers=admin_headers(state['super_admin_id'])))
    assert data['count'] >= 1
    assert any(u['code'] == state['user_code'] for u in data['users'])


def test_admin_list_filters():
    reviewing = expect(call('get', '/api/admin/users?status=reviewing',
                            headers=admin_headers(state['super_admin_id'])))
    assert all(u['status'] == 'reviewing' for u in reviewing['users'])

    scoped = expect(call('get', f"/api/admin/users?scope=mine&requesting_admin_id={state['super_admin_id']}",
                         headers=admin_headers(state['super_admin_id'])))
    assert all(u['assigned_admin_id'] == state['super_admin_id'] for u in scoped['users'])

    by_education = expect(call('get', '/api/admin/users?education=بكالوريوس',
                               headers=admin_headers(state['super_admin_id'])))
    assert by_education['count'] >= 1, 'education filter should match the seeded candidates'


def test_admin_updates_status_and_notifies_user():
    expect(call('put', f"/api/admin/users/{state['user_id']}/status",
                headers=admin_headers(state['super_admin_id']),
                body={'status': 'approved', 'status_reason': 'مطابق للمعايير'}))
    notif = expect(call('get', f"/api/notifications/user/{state['user_id']}",
                        headers=user_headers(state['user_code'])))
    assert len(notif['notifications']) >= 1


def test_admin_status_validation():
    expect(call('put', f"/api/admin/users/{state['user_id']}/status",
                headers=admin_headers(state['super_admin_id']), body={'status': 'hacked'}), 400)
    expect(call('put', '/api/admin/users/999999/status',
                headers=admin_headers(state['super_admin_id']), body={'status': 'approved'}), 404)


def test_admin_notes_visibility():
    uid = state['user_id']
    expect(call('post', f'/api/admin/users/{uid}/notes', headers=admin_headers(state['super_admin_id']),
                body={'note_text': 'ملاحظة مرئية للمتقدم', 'is_visible_to_user': True}), 201)
    expect(call('post', f'/api/admin/users/{uid}/notes', headers=admin_headers(state['super_admin_id']),
                body={'note_text': 'ملاحظة داخلية سرية', 'is_visible_to_user': False}), 201)

    profile = expect(call('get', f'/api/users/{uid}', headers=user_headers(state['user_code'])))
    visible = [n['note_text'] for n in profile['visible_notes']]
    assert 'ملاحظة مرئية للمتقدم' in visible
    assert 'ملاحظة داخلية سرية' not in visible, 'internal notes must never reach the applicant'

    all_notes = expect(call('get', f'/api/admin/users/{uid}/notes',
                            headers=admin_headers(state['super_admin_id'])))
    assert len(all_notes['notes']) >= 2


def test_admin_note_validation():
    expect(call('post', f"/api/admin/users/{state['user_id']}/notes",
                headers=admin_headers(state['super_admin_id']), body={'note_text': '   '}), 400)
    expect(call('post', '/api/admin/users/999999/notes',
                headers=admin_headers(state['super_admin_id']), body={'note_text': 'ملاحظة'}), 404)


def test_case_assignment():
    create = expect(call('post', '/api/admin/create', headers=admin_headers(state['super_admin_id']),
                         body={'full_name': 'إداري تجريبي', 'phone': '0500000001',
                               'email': 'regular.admin@test.com', 'city': 'الدوحة',
                               'password': 'RegularAdmin1'}), 201)
    state['regular_admin_id'] = create['admin_id']

    data = expect(call('put', f"/api/admin/users/{state['user_id']}/assign",
                       headers=admin_headers(state['super_admin_id']),
                       body={'target_admin_id': state['regular_admin_id']}))
    assert data['user']['assigned_admin_id'] == state['regular_admin_id']

    expect(call('put', f"/api/admin/users/{state['user_id']}/assign",
                headers=admin_headers(state['super_admin_id']),
                body={'target_admin_id': 999999}), 404)


def test_assignment_permission_boundary():
    """A regular admin may not reassign a case that is not theirs."""
    other_uid, _ = make_candidate('حالة أخرى', 'أنثى', '1997-07-07', approve=False)
    expect(call('put', f'/api/admin/users/{other_uid}/assign',
                headers=admin_headers(state['regular_admin_id']),
                body={'target_admin_id': state['regular_admin_id']}), 403)


def test_activity_log_records_actions():
    data = expect(call('get', '/api/admin/logs', headers=admin_headers(state['super_admin_id'])))
    kinds = {log['action_type'] for log in data['logs']}
    assert {'status_change', 'note_added', 'assignment', 'admin_created'} <= kinds, f'logged: {kinds}'

    filtered = expect(call('get', f"/api/admin/logs?user_id={state['user_id']}",
                           headers=admin_headers(state['super_admin_id'])))
    assert all(log['user_id'] == state['user_id'] for log in filtered['logs'])

    today = date.today().isoformat()
    ranged = expect(call('get', f'/api/admin/logs?date_from={today}',
                         headers=admin_headers(state['super_admin_id'])))
    assert ranged['count'] >= 1
    expect(call('get', '/api/admin/logs?date_from=2020-31-31',
                headers=admin_headers(state['super_admin_id'])), 400)


def test_system_log_file_written():
    from config import SYSTEM_LOG_FILE
    assert os.path.exists(SYSTEM_LOG_FILE), 'system.log should be created alongside DB activity logs'
    with open(SYSTEM_LOG_FILE, encoding='utf-8') as handle:
        assert 'action=status_change' in handle.read()


# ==========================================================================
# 5. ADMIN ACCOUNT MANAGEMENT
# ==========================================================================
def test_admin_creation_rules():
    expect(call('post', '/api/admin/create', headers=admin_headers(state['super_admin_id']),
                body={'full_name': 'ناقص'}), 400)
    expect(call('post', '/api/admin/create', headers=admin_headers(state['super_admin_id']),
                body={'full_name': 'مكرر', 'phone': '0500000004', 'email': 'regular.admin@test.com',
                      'city': 'الدوحة', 'password': 'DuplicatePass1'}), 409)


def test_admin_creation_requires_super_admin():
    expect(call('post', '/api/admin/create', headers=admin_headers(state['regular_admin_id']),
                body={'full_name': 'إداري غير مصرح', 'phone': '0500000002', 'email': 'hacker@test.com',
                      'city': 'الدوحة', 'password': 'HackerPass1'}), 403)


def test_admin_creation_rejects_weak_password():
    expect(call('post', '/api/admin/create', headers=admin_headers(state['super_admin_id']),
                body={'full_name': 'ضعيف', 'phone': '0500000003', 'email': 'weak@test.com',
                      'city': 'الدوحة', 'password': '123'}), 400)


def test_admin_creation_rejects_invalid_email():
    expect(call('post', '/api/admin/create', headers=admin_headers(state['super_admin_id']),
                body={'full_name': 'بريد خاطئ', 'phone': '0500000005', 'email': 'not-an-email',
                      'city': 'الدوحة', 'password': 'ValidPass123'}), 400)


def test_new_admin_can_log_in():
    data = expect(call('post', '/api/auth/admin-login',
                       body={'email': 'regular.admin@test.com', 'password': 'RegularAdmin1'}))
    assert data['admin']['is_super_admin'] is False


def test_admins_json_kept_in_sync():
    admins = read_json_file('admins.json')
    assert any(a['email'] == 'regular.admin@test.com' for a in admins['admins'])


def test_list_admins_detail_levels():
    full = expect(call('get', '/api/admin/admins', headers=admin_headers(state['super_admin_id'])))
    assert any(a['is_super_admin'] for a in full['admins'])
    assert 'email' in full['admins'][0], 'super admin sees full records'

    limited = expect(call('get', '/api/admin/admins', headers=admin_headers(state['regular_admin_id'])))
    assert all(set(a) == {'id', 'full_name'} for a in limited['admins']), \
        'regular admins must only see names, for assignment dropdowns'


def test_delete_admin_rules():
    expect(call('delete', f"/api/admin/admins/{state['super_admin_id']}",
                headers=admin_headers(state['super_admin_id']),
                body={'admin_id': state['super_admin_id']}), 400)
    expect(call('delete', f"/api/admin/admins/{state['regular_admin_id']}",
                headers=admin_headers(state['regular_admin_id']),
                body={'admin_id': state['regular_admin_id']}), 403)
    expect(call('delete', '/api/admin/admins/999999',
                headers=admin_headers(state['super_admin_id'])), 404)


def test_delete_user_and_code_reuse():
    gen = expect(call('post', '/api/admin/users/generate-code',
                      headers=admin_headers(state['super_admin_id']),
                      body={'full_name': 'للحذف'}), 201)
    uid, code = gen['user']['id'], gen['user']['code']
    expect(call('delete', f'/api/admin/users/{uid}', headers=admin_headers(state['super_admin_id'])))
    expect(call('post', '/api/auth/user-login', body={'code': code}), 404)

    nxt = expect(call('post', '/api/admin/users/generate-code',
                      headers=admin_headers(state['super_admin_id']),
                      body={'full_name': 'بعد الحذف'}), 201)
    assert nxt['user']['code'] != code, 'codes must not be recycled after a delete'


def test_generate_code_defaults_to_placeholder_name():
    gen = expect(call('post', '/api/admin/users/generate-code',
                      headers=admin_headers(state['super_admin_id']), body={}), 201)
    assert is_placeholder_name(gen['user']['full_name'])
    login = expect(call('post', '/api/auth/user-login', body={'code': gen['user']['code']}))
    assert login['user']['needs_onboarding'] is True


# ==========================================================================
# 6. AUTHORIZATION & SECURITY
# ==========================================================================
def test_admin_endpoints_require_authentication():
    unauthenticated = [
        ('get', '/api/admin/users', None),
        ('get', '/api/admin/admins', None),
        ('get', '/api/admin/logs', None),
        ('post', '/api/admin/users/generate-code', {'full_name': 'هاكر'}),
        ('put', f"/api/admin/users/{state['user_id']}/status", {'status': 'approved'}),
        ('post', f"/api/admin/users/{state['user_id']}/notes", {'note_text': 'اختراق'}),
        ('get', f"/api/admin/users/{state['user_id']}/notes", None),
        ('put', f"/api/admin/users/{state['user_id']}/assign", {'target_admin_id': 1}),
        ('delete', f"/api/admin/users/{state['user_id']}", None),
        ('post', '/api/admin/create', {'full_name': 'x', 'phone': '1', 'email': 'a@b.co',
                                       'city': 'c', 'password': 'Password12'}),
    ]
    leaks = []
    for method, path, body in unauthenticated:
        resp = call(method, path, body=body)
        if resp.status_code != 403:
            leaks.append(f'{method.upper()} {path} -> {resp.status_code}')
    assert not leaks, 'reachable without admin auth: ' + '; '.join(leaks)


def test_inactive_admin_has_no_access():
    resp = call('get', '/api/admin/users', headers=admin_headers(state['inactive_admin_id']))
    assert resp.status_code == 403, 'a deactivated admin must lose API access'


def test_user_registration_requires_admin():
    resp = call('post', '/api/users/register', body=sample_personal('مسجل بدون إذن'))
    assert resp.status_code == 403, 'self-registration must stay closed — codes are issued by admins'


def test_user_data_is_not_readable_without_credentials():
    expect(call('get', f"/api/users/{state['user_id']}"), 403)
    expect(call('get', f"/api/users/{state['user_id']}", headers=user_headers('WRONG999')), 403)


def test_user_cannot_write_to_another_account():
    victim_id = state['user_id']
    other_id, other_code = make_candidate('ضحية', 'أنثى', '1994-04-04', approve=False)
    state['second_user'] = (other_id, other_code)
    expect(call('put', f'/api/users/{victim_id}', headers=user_headers(other_code),
                body={'phone': '0599999999'}), 403)
    resp = call('post', f'/api/users/{victim_id}/answers', headers=user_headers(other_code),
                body={'mcq': sample_mcq(q4='المظهر'), 'open': sample_open(q1='إجابة محقونة')})
    assert resp.status_code == 403, 'answers must not be writable with another user code'


def test_completion_requires_matching_user_code():
    _, other_code = state['second_user']
    resp = call('post', f"/api/users/{state['user_id']}/complete", headers=user_headers(other_code),
                body={'personal': sample_personal('مخترق'), 'mcq': sample_mcq(), 'open': sample_open()})
    assert resp.status_code == 403, 'another user must not overwrite a profile via /complete'


def test_notifications_are_private():
    expect(call('get', f"/api/notifications/user/{state['user_id']}"), 403)
    _, other_code = state['second_user']
    expect(call('get', f"/api/notifications/user/{state['user_id']}",
                headers=user_headers(other_code)), 403)


def test_notification_read_authorization():
    notif = expect(call('get', f"/api/notifications/user/{state['user_id']}",
                        headers=user_headers(state['user_code'])))
    nid = notif['notifications'][0]['id']
    expect(call('put', f'/api/notifications/{nid}/read'), 403)
    _, other_code = state['second_user']
    expect(call('put', f'/api/notifications/{nid}/read', headers=user_headers(other_code)), 403)
    expect(call('put', f'/api/notifications/{nid}/read', headers=user_headers(state['user_code'])))
    expect(call('put', '/api/notifications/999999/read',
                headers=user_headers(state['user_code'])), 404)


def test_injection_payloads_are_stored_inertly():
    payload = "'; DROP TABLE users; --"
    uid, code = make_candidate('اختبار الحقن', 'أنثى', '1995-09-09', approve=False)
    expect(call('put', f'/api/users/{uid}', headers=user_headers(code),
                body={'guardian_relation': payload}))
    data = expect(call('get', f'/api/users/{uid}', headers=user_headers(code)))
    assert data['user']['guardian_relation'] == payload, 'stored verbatim, not executed'
    expect(call('get', '/api/admin/users', headers=admin_headers(state['super_admin_id'])))


def test_oversized_input_is_truncated_not_stored_whole():
    uid, code = make_candidate('حقل طويل', 'أنثى', '1993-03-03', approve=False)
    expect(call('put', f'/api/users/{uid}', headers=user_headers(code), body={'phone': '9' * 500}))
    data = expect(call('get', f'/api/users/{uid}', headers=user_headers(code)))
    assert len(data['user']['phone'] or '') <= 20, 'phone must be capped to the column width'


# ==========================================================================
# 7. MATCHING ENGINE (unit level)
# ==========================================================================
def test_factor_discovery_is_configuration_driven():
    expected = len([q for q in QUESTIONS['mcq'] if q.get('matching')])
    for step in QUESTIONS['onboarding']['steps']:
        items = step.get('fields', []) if step.get('type') == 'preferences' else [step]
        expected += len([item for item in items if item.get('matching')])
    assert len(matching_factors()) == expected, \
        f'discovered {len(matching_factors())}, configuration declares {expected}'


def test_ordinal_scoring():
    config = {'matching_order': ['ثانوي', 'دبلوم', 'بكالوريوس']}
    assert score_ordinal('ثانوي', 'ثانوي', config) == 100.0
    assert score_ordinal('ثانوي', 'بكالوريوس', config) == 0.0
    assert score_ordinal('ثانوي', 'مجهول', config) is None
    neutral = {**config, 'matching_neutral_options': ['لا يهم']}
    assert score_ordinal('لا يهم', 'ثانوي', neutral) == 100.0


def test_numeric_boolean_and_multiselect_scoring():
    assert score_numeric(10, 10, {}) == 100.0
    assert score_numeric(10, 15, {'matching_tolerance': 10}) == 50.0
    assert score_numeric('abc', 1, {}) is None
    assert score_boolean('نعم', True, {}) == 100.0
    assert score_multi_select(['a', 'b'], ['b'], {}) == 50.0
    assert score_multi_select('a', ['b'], {}) is None


def test_eligibility_rules():
    class Fake:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    male = Fake(id=1, gender='ذكر', birthday=date(1990, 1, 1), profile=Fake(details={'x': 1}), status='approved')
    female = Fake(id=2, gender='أنثى', birthday=date(1992, 1, 1), profile=Fake(details={'x': 1}), status='approved')
    assert evaluate_eligibility(male, female, allowed_statuses=('approved',))['eligible'] is True
    assert evaluate_eligibility(male, male)['eligible'] is False, 'self-match must be rejected'

    same_gender = Fake(id=3, gender='ذكر', birthday=date(1991, 1, 1), profile=Fake(details={}), status='approved')
    assert evaluate_eligibility(male, same_gender)['checks']['opposite_gender'] is False
    pending = Fake(id=4, gender='أنثى', birthday=date(1992, 1, 1), profile=Fake(details={}), status='pending')
    assert evaluate_eligibility(male, pending, allowed_statuses=('approved',))['eligible'] is False


def test_compute_age_handles_birthday_boundary():
    today = date(2026, 5, 14)
    assert compute_age(date(1998, 5, 15), today=today) == 27
    assert compute_age(date(1998, 5, 14), today=today) == 28
    assert compute_age(None) is None


# ==========================================================================
# 8. MATCHING ENDPOINTS
# ==========================================================================
def test_admin_pair_scoring():
    male_id, male_code = make_candidate('محمد علي', 'ذكر', '1995-03-10')
    state['male_id'], state['male_code'] = male_id, male_code

    data = expect(call('get', f"/api/admin/matches/pair?user_a={state['user_id']}&user_b={male_id}",
                       headers=admin_headers(state['super_admin_id'])))
    match = data['match']
    assert match['eligible'] is True
    assert match['has_sufficient_data'] is True
    assert 0 <= match['compatibility_percentage'] <= 100
    assert match['applicable_factors'] > 0
    assert set(match['breakdown']) <= {str(f['key']) for f in matching_factors()}


def test_pair_scoring_validation():
    expect(call('get', '/api/admin/matches/pair?user_a=1',
                headers=admin_headers(state['super_admin_id'])), 400)
    expect(call('get', '/api/admin/matches/pair?user_a=1&user_b=1',
                headers=admin_headers(state['super_admin_id'])), 400)
    expect(call('get', '/api/admin/matches/pair?user_a=1&user_b=999999',
                headers=admin_headers(state['super_admin_id'])), 404)


def test_same_gender_pair_is_ineligible():
    female2_id, _ = make_candidate('هند سالم', 'أنثى', '1997-01-20')
    state['female2_id'] = female2_id
    data = expect(call('get', f"/api/admin/matches/pair?user_a={state['user_id']}&user_b={female2_id}",
                       headers=admin_headers(state['super_admin_id'])))
    assert data['match']['eligible'] is False
    assert data['match']['eligibility']['checks']['opposite_gender'] is False


def test_admin_match_list_is_ranked_and_filtered():
    data = expect(call('get', f"/api/admin/users/{state['user_id']}/matches?status=approved&limit=10",
                       headers=admin_headers(state['super_admin_id'])))
    scores = [m['compatibility_percentage'] for m in data['matches']]
    assert scores == sorted(scores, reverse=True), 'matches must be ranked by score'
    assert all(m['candidate']['gender'] == 'ذكر' for m in data['matches']), 'opposite gender only'

    high_bar = expect(call('get', f"/api/admin/users/{state['user_id']}/matches?min_score=101",
                           headers=admin_headers(state['super_admin_id'])))
    assert high_bar['count'] == 0

    expect(call('get', f"/api/admin/users/{state['user_id']}/matches?status=bogus",
                headers=admin_headers(state['super_admin_id'])), 400)
    expect(call('get', '/api/admin/users/999999/matches',
                headers=admin_headers(state['super_admin_id'])), 404)


def test_matching_endpoints_require_admin():
    expect(call('get', f"/api/admin/users/{state['user_id']}/matches"), 403)
    expect(call('get', '/api/admin/matches/pair?user_a=1&user_b=2'), 403)


def test_public_matches_are_privacy_safe():
    data = expect(call('get', f"/api/admin/public/users/{state['user_id']}/matches",
                       headers=user_headers(state['user_code'])))
    assert data['count'] >= 1
    leaked = []
    for match in data['matches']:
        candidate = match['candidate']
        assert 'candidate_ref' in candidate
        leaked += [field for field in ('full_name', 'code', 'email', 'phone', 'id') if field in candidate]
        assert 'compatibility_summary' in match
    assert not leaked, f'identity fields exposed to candidates: {sorted(set(leaked))}'


def test_public_matches_require_approved_self():
    expect(call('get', f"/api/admin/public/users/{state['user_id']}/matches"), 403)
    pending_id, pending_code = make_candidate('غير معتمد', 'أنثى', '1999-11-11', approve=False)
    state['pending_user'] = (pending_id, pending_code)
    expect(call('get', f'/api/admin/public/users/{pending_id}/matches',
                headers=user_headers(pending_code)), 403)


# ==========================================================================
# 9. CANDIDATE INTERACTIONS (saved candidates + compatibility requests)
# ==========================================================================
def test_save_and_list_and_remove_candidate():
    male_ref = state['male_id']
    expect(call('post', '/api/matching/saved', headers=user_headers(state['user_code']),
                body={'candidate_id': male_ref}))
    saved = expect(call('get', '/api/matching/saved', headers=user_headers(state['user_code'])))
    assert any(item['candidate_ref'] == male_ref for item in saved['saved'])
    assert all('full_name' not in (item['candidate'] or {}) for item in saved['saved'])

    # saving twice must stay idempotent rather than duplicating or erroring
    expect(call('post', '/api/matching/saved', headers=user_headers(state['user_code']),
                body={'candidate_id': male_ref}))
    again = expect(call('get', '/api/matching/saved', headers=user_headers(state['user_code'])))
    assert len(again['saved']) == len(saved['saved'])

    expect(call('delete', f'/api/matching/saved/{male_ref}', headers=user_headers(state['user_code'])))
    expect(call('delete', f'/api/matching/saved/{male_ref}', headers=user_headers(state['user_code'])), 404)


def test_save_validation():
    expect(call('post', '/api/matching/saved', headers=user_headers(state['user_code']),
                body={'candidate_id': 'abc'}), 400)
    expect(call('post', '/api/matching/saved', headers=user_headers(state['user_code']),
                body={'candidate_id': state['user_id']}), 400)
    expect(call('post', '/api/matching/saved', headers=user_headers(state['user_code']),
                body={'candidate_id': 999999}), 404)
    expect(call('post', '/api/matching/saved', headers=user_headers(state['user_code']),
                body={'candidate_id': state['female2_id']}), 400)


def test_compatibility_request_round_trip():
    created = expect(call('post', '/api/matching/requests', headers=user_headers(state['user_code']),
                          body={'candidate_id': state['male_id']}), 201)
    state['request_id'] = created['request']['id']
    assert created['request']['status'] == 'pending'

    notif = expect(call('get', f"/api/notifications/user/{state['male_id']}",
                        headers=user_headers(state['male_code'])))
    assert any('طلب توافق' in n['message'] for n in notif['notifications'])

    incoming = expect(call('get', '/api/matching/requests', headers=user_headers(state['male_code'])))
    assert any(r['id'] == state['request_id'] for r in incoming['incoming'])
    sent = expect(call('get', '/api/matching/requests', headers=user_headers(state['user_code'])))
    assert any(r['id'] == state['request_id'] for r in sent['sent'])


def test_duplicate_request_is_deduplicated():
    resp = expect(call('post', '/api/matching/requests', headers=user_headers(state['user_code']),
                       body={'candidate_id': state['male_id']}))
    assert resp['request']['id'] == state['request_id'], 'must reuse the existing request, not duplicate'


def test_only_receiver_can_answer_a_request():
    expect(call('put', f"/api/matching/requests/{state['request_id']}",
                headers=user_headers(state['user_code']), body={'status': 'accepted'}), 403)
    expect(call('put', f"/api/matching/requests/{state['request_id']}",
                headers=user_headers(state['male_code']), body={'status': 'maybe'}), 400)
    expect(call('put', '/api/matching/requests/999999',
                headers=user_headers(state['male_code']), body={'status': 'accepted'}), 404)


def test_accepting_a_request_notifies_sender_and_locks_it():
    expect(call('put', f"/api/matching/requests/{state['request_id']}",
                headers=user_headers(state['male_code']), body={'status': 'accepted'}))
    notif = expect(call('get', f"/api/notifications/user/{state['user_id']}",
                        headers=user_headers(state['user_code'])))
    assert any('تم قبول' in n['message'] for n in notif['notifications'])
    expect(call('put', f"/api/matching/requests/{state['request_id']}",
                headers=user_headers(state['male_code']), body={'status': 'declined'}), 409)


def test_interactions_require_approved_login():
    for method, path in (('get', '/api/matching/requests'), ('get', '/api/matching/saved')):
        expect(call(method, path), 403)
    _, pending_code = state['pending_user']
    expect(call('get', '/api/matching/requests', headers=user_headers(pending_code)), 403)
    expect(call('post', '/api/matching/saved', headers=user_headers(pending_code),
                body={'candidate_id': state['male_id']}), 403)


# ==========================================================================
# 10. UPLOADS, JSON SYNC & UTILITIES
# ==========================================================================
def test_uploaded_photo_is_served():
    from werkzeug.datastructures import FileStorage
    from utils import save_user_photo

    storage = FileStorage(stream=io.BytesIO(b'\x89PNG\r\n\x1a\nfake'), filename='avatar.png')
    filename, error = save_user_photo(storage)
    assert error is None and filename
    resp = client.get(f'/uploads/{filename}')
    assert resp.status_code == 200, f'uploaded file not served: HTTP {resp.status_code}'


def test_photo_upload_rejects_bad_extension():
    from werkzeug.datastructures import FileStorage
    from utils import save_user_photo

    storage = FileStorage(stream=io.BytesIO(b'MZ'), filename='payload.exe')
    filename, error = save_user_photo(storage)
    assert filename is None and error, 'executable uploads must be rejected'


def test_photo_url_honours_public_base_url():
    original = os.environ.get('WEFAQ_PUBLIC_BASE_URL')
    os.environ['WEFAQ_PUBLIC_BASE_URL'] = 'https://images.example.com'
    try:
        with app.test_request_context('/'):
            assert photo_url_for('avatar.png') == 'https://images.example.com/uploads/avatar.png'
            assert photo_url_for('') is None
            assert photo_url_for('https://cdn.example.com/x.png') == 'https://cdn.example.com/x.png'
    finally:
        os.environ.pop('WEFAQ_PUBLIC_BASE_URL', None)
        if original:
            os.environ['WEFAQ_PUBLIC_BASE_URL'] = original


def test_password_hashing_round_trip():
    digest = hash_password('SecretPass123')
    assert digest != 'SecretPass123'
    assert verify_password(digest, 'SecretPass123')
    assert not verify_password(digest, 'SecretPass124')


def test_validators():
    assert validate_email('User@Example.COM ') == 'user@example.com'
    assert validate_email('bad@@example') is None
    assert validate_email('') is None
    assert sanitize_text('  hi\x00there  ') == 'hithere'
    assert sanitize_text(None) == ''
    assert sanitize_text('abcdef', 3) == 'abc'
    assert validate_birthday('1990-01-01')[0] == date(1990, 1, 1)
    assert validate_birthday('2030-01-01')[0] is None
    assert validate_text_answer('نص حقيقي')[0] == 'نص حقيقي'
    assert validate_text_answer('12345')[0] is None, 'digits-only is not a real answer'


def test_users_json_sync_reflects_database():
    users = read_json_file('users.json') or []
    codes = {u.get('code') for u in users}
    assert state['user_code'] in codes, 'completed applicants should appear in users.json'
    entry = next(u for u in users if u['code'] == state['user_code'])
    assert entry.get('profile_details'), 'sync must carry profile details'
    assert entry.get('open_answers'), 'sync must carry open answers'


def test_deleted_user_removed_from_json():
    gen = expect(call('post', '/api/admin/users/generate-code',
                      headers=admin_headers(state['super_admin_id']),
                      body={'full_name': 'حذف من الملف'}), 201)
    uid = gen['user']['id']
    expect(call('delete', f'/api/admin/users/{uid}', headers=admin_headers(state['super_admin_id'])))
    users = read_json_file('users.json') or []
    assert all(u.get('id') != uid for u in users)


def test_cascade_delete_cleans_related_rows():
    uid, _ = make_candidate('حذف متسلسل', 'أنثى', '1992-12-12')
    expect(call('post', f'/api/admin/users/{uid}/notes', headers=admin_headers(state['super_admin_id']),
                body={'note_text': 'ملاحظة قبل الحذف'}), 201)
    expect(call('delete', f'/api/admin/users/{uid}', headers=admin_headers(state['super_admin_id'])))
    with app.app_context():
        assert Notification.query.filter_by(user_id=uid).count() == 0
        assert MCQAnswer.query.filter_by(user_id=uid).count() == 0


def test_cors_allows_frontend_auth_headers():
    resp = client.options('/api/admin/users', headers={
        'Origin': 'http://localhost:5173',
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'X-Admin-Id',
    })
    allowed = resp.headers.get('Access-Control-Allow-Headers', '')
    assert 'X-Admin-Id' in allowed, f'CORS must allow the auth header, got: {allowed!r}'


# ==========================================================================
# runner
# ==========================================================================
GROUPS = [
    ('AUTHENTICATION', [
        test_admin_login_success, test_admin_login_is_case_insensitive,
        test_admin_login_wrong_password_rejected, test_admin_login_missing_fields_rejected,
        test_inactive_admin_cannot_login, test_user_login_flow, test_user_login_bad_code_rejected,
    ]),
    ('QUESTIONS & ONBOARDING CONFIG', [
        test_questions_endpoint_matches_configuration, test_every_matching_question_is_well_formed,
    ]),
    ('USER LIFECYCLE', [
        test_complete_application, test_completed_user_no_longer_needs_onboarding,
        test_complete_rejects_incomplete_mcq, test_complete_rejects_missing_open_answers,
        test_complete_rejects_missing_profile_details, test_complete_rejects_placeholder_name,
        test_complete_rejects_underage_and_future_birthdays, test_get_own_profile,
        test_update_own_profile, test_update_rejects_placeholder_name_and_bad_birthday,
        test_save_answers_endpoint, test_unknown_user_returns_404,
    ]),
    ('ADMIN CASE MANAGEMENT', [
        test_admin_lists_users, test_admin_list_filters, test_admin_updates_status_and_notifies_user,
        test_admin_status_validation, test_admin_notes_visibility, test_admin_note_validation,
        test_case_assignment, test_assignment_permission_boundary,
        test_activity_log_records_actions, test_system_log_file_written,
    ]),
    ('ADMIN ACCOUNTS', [
        test_admin_creation_rules, test_admin_creation_requires_super_admin,
        test_admin_creation_rejects_weak_password, test_admin_creation_rejects_invalid_email,
        test_new_admin_can_log_in, test_admins_json_kept_in_sync, test_list_admins_detail_levels,
        test_delete_admin_rules, test_delete_user_and_code_reuse,
        test_generate_code_defaults_to_placeholder_name,
    ]),
    ('AUTHORIZATION & SECURITY', [
        test_admin_endpoints_require_authentication, test_inactive_admin_has_no_access,
        test_user_registration_requires_admin, test_user_data_is_not_readable_without_credentials,
        test_user_cannot_write_to_another_account, test_completion_requires_matching_user_code,
        test_notifications_are_private, test_notification_read_authorization,
        test_injection_payloads_are_stored_inertly, test_oversized_input_is_truncated_not_stored_whole,
    ]),
    ('MATCHING ENGINE', [
        test_factor_discovery_is_configuration_driven, test_ordinal_scoring,
        test_numeric_boolean_and_multiselect_scoring, test_eligibility_rules,
        test_compute_age_handles_birthday_boundary,
    ]),
    ('MATCHING ENDPOINTS', [
        test_admin_pair_scoring, test_pair_scoring_validation, test_same_gender_pair_is_ineligible,
        test_admin_match_list_is_ranked_and_filtered, test_matching_endpoints_require_admin,
        test_public_matches_are_privacy_safe, test_public_matches_require_approved_self,
    ]),
    ('CANDIDATE INTERACTIONS', [
        test_save_and_list_and_remove_candidate, test_save_validation,
        test_compatibility_request_round_trip, test_duplicate_request_is_deduplicated,
        test_only_receiver_can_answer_a_request, test_accepting_a_request_notifies_sender_and_locks_it,
        test_interactions_require_approved_login,
    ]),
    ('UPLOADS, SYNC & UTILITIES', [
        test_uploaded_photo_is_served, test_photo_upload_rejects_bad_extension,
        test_photo_url_honours_public_base_url, test_password_hashing_round_trip, test_validators,
        test_users_json_sync_reflects_database, test_deleted_user_removed_from_json,
        test_cascade_delete_cleans_related_rows, test_cors_allows_frontend_auth_headers,
    ]),
]


def main():
    print('WEFAQ — Full Feature Test Suite')
    print(f'Isolated test dir: {TEST_ROOT}\n')
    passed, failures = 0, []

    for label, tests in GROUPS:
        print('=' * 68)
        print(f'  {label}')
        print('=' * 68)
        for test in tests:
            name = test.__name__
            try:
                test()
            except AssertionError as exc:
                failures.append((label, name, str(exc) or 'assertion failed'))
                print(f'  ✗ FAIL  {name}: {exc}')
            except Exception as exc:  # noqa: BLE001 - report, never abort the whole suite
                detail = f'{type(exc).__name__}: {exc}'
                failures.append((label, name, detail))
                print(f'  ✗ ERROR {name}: {detail}')
                traceback.print_exc(limit=2)
            else:
                passed += 1
                print(f'  ✓ PASS  {name}')
        print()

    print('=' * 68)
    print(f'  RESULT: {passed} passed, {len(failures)} failed')
    print('=' * 68)
    if failures:
        print('\nFAILURES\n--------')
        for label, name, detail in failures:
            print(f'[{label}] {name}\n    {detail}\n')
    return 1 if failures else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    finally:
        shutil.rmtree(TEST_ROOT, ignore_errors=True)
