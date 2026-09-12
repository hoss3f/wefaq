# backend/routes/user_routes.py
from datetime import datetime
from flask import Blueprint, request, jsonify
from models import db, User, UserProfile, MCQAnswer, OpenAnswer, AdminNote
from utils import (
    load_questions,
    generate_user_code,
    sync_user_to_json,
    user_needs_onboarding,
    is_placeholder_name,
    save_user_photo,
    photo_url_for,
    send_welcome_email,
)
from security import can_read_user, require_user_self, sanitize_text, validate_email, MAX_PHONE_LEN

user_bp = Blueprint('user', __name__, url_prefix='/api')

REQUIRED_FIELDS = ['full_name', 'birthday', 'gender', 'country']
UPDATABLE_FIELDS = [
    'full_name', 'phone', 'email', 'gender', 'country',
    'guardian_phone', 'guardian_relation'
]

MARITAL_OPTIONS = {
    'ذكر': {'أعزب', 'متزوج', 'مطلق', 'أرمل'},
    'أنثى': {'عزباء', 'متزوجة', 'مطلقة', 'أرملة'},
}
LEGACY_MARITAL_OPTIONS = {'لم أتزوج من قبل', 'متزوج سابقاً'}
SKIN_TONE_OPTIONS = {'فاتح', 'قمحي', 'أسمر', 'داكن'}
BODY_TYPE_OPTIONS = {'نحيف', 'متوسط', 'رياضي', 'ممتلئ'}
REGISTRANT_RELATIONS = {'أنا صاحب الطلب', 'أنا وليّ أمر صاحب الطلب', 'أنا أحد أفراد أسرته'}


def _parse_birthday(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def _valid_full_name(value):
    name = sanitize_text(value, 100)
    return name if 2 <= len(name) <= 100 and any(character.isalpha() for character in name) else None


def _preference_nationalities():
    questions = load_questions() or {}
    for step in questions.get('onboarding', {}).get('steps', []):
        for field in step.get('fields', []):
            if field.get('key') == 'nationality_preference':
                return set(field.get('options') or [])
    return set()


def _validate_profile_details(details, gender):
    if not isinstance(details, dict):
        return None, 'بيانات الملف غير صالحة.'
    normalized = dict(details)
    required = ['registrant_relation', 'nationality', 'profession', 'marital_status', 'marriage_timeline', 'height', 'weight', 'skin_tone', 'body_type']
    if gender == 'أنثى':
        required.append('polygyny_acceptance')
    missing = [field for field in required if normalized.get(field) in (None, '', [])]
    if missing:
        return None, 'يرجى إكمال جميع بيانات الملف المطلوبة.'

    allowed_marital = MARITAL_OPTIONS.get(gender, set()) | LEGACY_MARITAL_OPTIONS
    if normalized.get('marital_status') not in allowed_marital:
        return None, 'الحالة الاجتماعية غير صالحة.'
    if normalized.get('skin_tone') not in SKIN_TONE_OPTIONS:
        return None, 'قيمة لون البشرة غير صالحة.'
    if normalized.get('body_type') not in BODY_TYPE_OPTIONS:
        return None, 'قيمة القوام غير صالحة.'
    if normalized.get('registrant_relation') not in REGISTRANT_RELATIONS:
        return None, 'صلة المسجّل بصاحب الطلب غير صالحة.'
    if gender == 'أنثى' and normalized.get('polygyny_acceptance') not in ('نعم', 'لا'):
        return None, 'يرجى تحديد الإجابة المتعلقة بتعدد الزوجات.'
    if gender != 'أنثى' and normalized.get('polygyny_acceptance') not in (None, ''):
        return None, 'هذا الحقل مخصص للمرشحات فقط.'

    nationalities = normalized.get('nationality_preference')
    if isinstance(nationalities, str):
        nationalities = [nationalities]
    if not isinstance(nationalities, list) or not nationalities:
        return None, 'يرجى اختيار جنسية مفضلة واحدة على الأقل.'
    cleaned = [sanitize_text(value, 60) for value in nationalities]
    if any(not value for value in cleaned) or len(cleaned) != len(set(cleaned)):
        return None, 'قائمة الجنسيات المفضلة غير صالحة أو تحتوي على تكرار.'
    allowed_nationalities = _preference_nationalities()
    if allowed_nationalities and any(value not in allowed_nationalities for value in cleaned):
        return None, 'تحتوي قائمة الجنسيات المفضلة على قيمة غير معتمدة.'
    if 'لا يهم' in cleaned and len(cleaned) > 1:
        return None, 'لا يمكن جمع خيار «لا يهم» مع جنسيات أخرى.'
    normalized['nationality_preference'] = cleaned
    return normalized, None


def _validate_open_answers(open_data):
    for number in range(1, 5):
        answer = sanitize_text(open_data.get(f'q{number}'), 1500)
        minimum = 20 if number == 1 else 5
        if len(answer) < minimum:
            return False, 'يرجى كتابة إجابة أوضح قبل المتابعة.'
        open_data[f'q{number}'] = answer
    return True, None


def _apply_personal_data(user, data):
    """تطبيق البيانات الشخصية على كائن المستخدم مع التحقق"""
    missing = [field for field in REQUIRED_FIELDS if not data.get(field)]
    if missing:
        return False, {'success': False, 'message': 'حقول ناقصة', 'missing_fields': missing}, 400

    full_name = _valid_full_name(data.get('full_name'))
    if not full_name or is_placeholder_name(full_name):
        return False, {'success': False, 'message': 'يرجى إدخال الاسم الكامل الحقيقي.'}, 400

    birthday = _parse_birthday(data.get('birthday'))
    if not birthday:
        return False, {'success': False, 'message': 'صيغة تاريخ الميلاد غير صحيحة'}, 400

    user.full_name = full_name
    user.birthday = birthday
    user.gender = data['gender']
    user.country = data['country']

    if 'phone' in data:
        user.phone = sanitize_text(data.get('phone', ''), MAX_PHONE_LEN)

    if data.get('email'):
        email = validate_email(data.get('email'))
        if not email:
            return False, {'success': False, 'message': 'البريد الإلكتروني غير صحيح'}, 400
        user.email = email
    elif 'email' in data:
        user.email = ''

    details, detail_error = _validate_profile_details(data.get('profile_details') or {}, user.gender)
    if detail_error:
        return False, {'success': False, 'message': detail_error}, 400
    profile = UserProfile.query.filter_by(user_id=user.id).first() or UserProfile(user_id=user.id)
    profile.details = details
    db.session.add(profile)
    if 'photo_path' in data:
        user.photo_path = data.get('photo_path') or ''
    return True, None, None


def _upsert_answers(user_id, mcq_data, open_data):
    mcq_answer = MCQAnswer.query.filter_by(user_id=user_id).first() or MCQAnswer(user_id=user_id)
    mcq_answer.answers = {
        **(mcq_answer.answers or {}),
        **{key: value for key, value in mcq_data.items() if value is not None},
    }
    # نواصل ملء الأعمدة القديمة كي لا تتأثر البيانات والمسارات السابقة.
    for number in range(1, 5):
        key = f'q{number}'
        if key in mcq_data:
            setattr(mcq_answer, key, mcq_data[key])

    open_answer = OpenAnswer.query.filter_by(user_id=user_id).first() or OpenAnswer(user_id=user_id)
    open_answer.q1 = open_data.get('q1', open_answer.q1 if open_answer.id else None)
    open_answer.q2 = open_data.get('q2', open_answer.q2 if open_answer.id else None)
    open_answer.q3 = open_data.get('q3', open_answer.q3 if open_answer.id else None)
    open_answer.q4 = open_data.get('q4', open_answer.q4 if open_answer.id else None)

    db.session.add(mcq_answer)
    db.session.add(open_answer)
    return mcq_answer, open_answer


def _parse_registration_data():
    """قراءة بيانات التسجيل من JSON أو multipart/form-data"""
    if request.content_type and 'multipart/form-data' in request.content_type:
        return request.form.to_dict(), request.files.get('photo')
    return request.get_json() or {}, None


def _user_payload(user, needs=None):
    return {
        'id': user.id,
        'code': user.code,
        'full_name': user.full_name,
        'phone': user.phone,
        'email': user.email,
        'birthday': user.birthday.isoformat() if user.birthday else None,
        'gender': user.gender,
        'country': user.country,
        'guardian_phone': user.guardian_phone,
        'guardian_relation': user.guardian_relation,
        'photo_url': photo_url_for(user.photo_path),
        'status': user.status,
        'status_reason': user.status_reason,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'needs_onboarding': needs if needs is not None else user_needs_onboarding(user)
    }


@user_bp.route('/questions', methods=['GET'])
def get_questions():
    """إرجاع أسئلة الاختيار من متعدد والأسئلة المفتوحة لعرضها في نموذج التسجيل"""
    questions = load_questions()
    if not questions:
        return jsonify({'success': False, 'message': 'تعذر تحميل الأسئلة'}), 500
    return jsonify({'success': True, 'questions': questions}), 200


@user_bp.route('/users/register', methods=['POST'])
def register_user():
    """تسجيل مستخدم جديد — يتطلب مصادقة إدارية"""
    data, photo_file = _parse_registration_data()
    """تسجيل مستخدم جديد وإصدار كود خاص به"""
    data = request.get_json() or {}

    missing = [field for field in REQUIRED_FIELDS if not data.get(field)]
    if missing:
        return jsonify({
            'success': False,
            'message': 'حقول ناقصة',
            'missing_fields': missing
        }), 400

    full_name = _valid_full_name(data.get('full_name'))
    if not full_name or is_placeholder_name(full_name):
        return jsonify({'success': False, 'message': 'يرجى إدخال الاسم الكامل الحقيقي.'}), 400

    birthday = _parse_birthday(data.get('birthday'))
    if not birthday:
        return jsonify({'success': False, 'message': 'صيغة تاريخ الميلاد غير صحيحة'}), 400

    email = validate_email(data.get('email'))
    if not email:
        return jsonify({'success': False, 'message': 'البريد الإلكتروني غير صحيح'}), 400

    photo_path = sanitize_text(data.get('photo_path', ''), 200) or None
    if photo_file and photo_file.filename:
        filename, photo_err = save_user_photo(photo_file)
        if photo_err:
            return jsonify({'success': False, 'message': photo_err}), 400
        photo_path = filename

    new_user = User(
        code=generate_user_code(User),
        full_name=full_name,
        phone=data['phone'],
        email=data['email'],
        birthday=birthday,
        gender=sanitize_text(data['gender'], 10),
        guardian_phone=sanitize_text(data.get('guardian_phone', ''), 20),
        guardian_relation=sanitize_text(data.get('guardian_relation', ''), 50),
        photo_path=photo_path,
        country=sanitize_text(data['country'], 50),
        status='pending'
    )
    db.session.add(new_user)
    db.session.commit()
    sync_user_to_json(new_user)

    return jsonify({
        'success': True,
        'message': 'تم إنشاء الحساب بنجاح',
        'user': {'id': new_user.id, 'code': new_user.code, 'photo_url': photo_url_for(new_user.photo_path)}
    }), 201


@user_bp.route('/users/<int:user_id>/answers', methods=['POST'])
def save_answers(user_id):
    """حفظ إجابات الأسئلة المغلقة والمفتوحة لمستخدم معيّن"""
    user, error = require_user_self(user_id)
    if error:
        return error

    data = request.get_json() or {}
    mcq_data = data.get('mcq', {})
    open_data = data.get('open', {})

    _upsert_answers(user_id, mcq_data, open_data)
    user.status = 'reviewing'
    db.session.commit()
    sync_user_to_json(user)

    return jsonify({'success': True, 'message': 'تم حفظ الإجابات بنجاح'}), 200


@user_bp.route('/users/<int:user_id>/complete', methods=['POST'])
def complete_application(user_id):
    """
    إكمال طلب مستخدم بالكود لأول مرة:
    حفظ البيانات الشخصية + الإجابات في طلب واحد ثم تحويل الحالة إلى قيد المراجعة.
    """
    user, error = require_user_self(user_id)
    if error:
        return error

    data = request.get_json() or {}
    personal = data.get('personal') or data
    mcq_data = data.get('mcq') or {}
    open_data = data.get('open') or {}

    required_mcq = [
        question.get('answer_key') or f"q{question['id']}"
        for question in (load_questions() or {}).get('mcq', [])
        if question.get('matching')
    ]
    missing_mcq = [key for key in required_mcq if not mcq_data.get(key)]
    if missing_mcq:
        return jsonify({
            'success': False,
            'message': 'يرجى الإجابة عن جميع أسئلة التوافق',
            'missing_fields': missing_mcq,
        }), 400

    ok, err_body, err_code = _apply_personal_data(user, personal)
    if not ok:
        return jsonify(err_body), err_code

    open_ok, open_error = _validate_open_answers(open_data)
    if not open_ok:
        return jsonify({'success': False, 'message': open_error}), 400

    _upsert_answers(user_id, mcq_data, open_data)
    user.status = 'reviewing'
    db.session.commit()
    sync_user_to_json(user)
    send_welcome_email(user)

    mcq = MCQAnswer.query.filter_by(user_id=user_id).first()
    open_ans = OpenAnswer.query.filter_by(user_id=user_id).first()

    return jsonify({
        'success': True,
        'message': 'تم إكمال الطلب بنجاح',
        'user': _user_payload(user, needs=False),
        'mcq_answers': {
            'q1': mcq.q1, 'q2': mcq.q2, 'q3': mcq.q3, 'q4': mcq.q4
        } if mcq else None,
        'profile_details': user.profile.details if user.profile else {},
        'open_answers': {
            'q1': open_ans.q1, 'q2': open_ans.q2, 'q3': open_ans.q3, 'q4': open_ans.q4
        } if open_ans else None
    }), 200


@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """إرجاع بيانات المستخدم مع إجاباته والملاحظات المرئية له"""
    user, error = can_read_user(user_id)
    if error:
        return error

    mcq = MCQAnswer.query.filter_by(user_id=user_id).first()
    open_ans = OpenAnswer.query.filter_by(user_id=user_id).first()
    needs = user_needs_onboarding(user, mcq_answer=mcq)

    visible_notes = (
        AdminNote.query
        .filter_by(user_id=user_id, is_visible_to_user=True)
        .order_by(AdminNote.created_at.desc())
        .all()
    )

    return jsonify({
        'success': True,
        'user': _user_payload(user, needs=needs),
        'mcq_answers': {
            'q1': mcq.q1, 'q2': mcq.q2, 'q3': mcq.q3, 'q4': mcq.q4
        } if mcq else None,
        'profile_details': user.profile.details if user.profile else {},
        'open_answers': {
            'q1': open_ans.q1, 'q2': open_ans.q2, 'q3': open_ans.q3, 'q4': open_ans.q4
        } if open_ans else None,
        'visible_notes': [{
            'id': n.id,
            'admin_name': n.admin.full_name if n.admin else None,
            'note_text': n.note_text,
            'created_at': n.created_at.isoformat() if n.created_at else None
        } for n in visible_notes]
    }), 200


@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """تحديث البيانات الشخصية للمستخدم"""
    user, error = require_user_self(user_id)
    if error:
        return error

    data = request.get_json() or {}

    for field in UPDATABLE_FIELDS:
        if field in data and data[field] is not None:
            value = data[field]
            if field == 'full_name':
                value = _valid_full_name(value)
                if not value or is_placeholder_name(value):
                    return jsonify({'success': False, 'message': 'يرجى إدخال الاسم الكامل الحقيقي.'}), 400
            setattr(user, field, value)

    if 'birthday' in data and data['birthday']:
        birthday = _parse_birthday(data['birthday'])
        if not birthday:
            return jsonify({'success': False, 'message': 'صيغة تاريخ الميلاد غير صحيحة'}), 400
        user.birthday = birthday

    db.session.commit()
    sync_user_to_json(user)

    return jsonify({
        'success': True,
        'message': 'تم تحديث البيانات بنجاح',
        'user': _user_payload(user)
    }), 200
