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
)

user_bp = Blueprint('user', __name__, url_prefix='/api')

REQUIRED_FIELDS = ['full_name', 'birthday', 'gender', 'country']
UPDATABLE_FIELDS = [
    'full_name', 'phone', 'email', 'gender', 'country',
    'guardian_phone', 'guardian_relation'
]


def _parse_birthday(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def _apply_personal_data(user, data):
    """تطبيق البيانات الشخصية على كائن المستخدم مع التحقق"""
    missing = [field for field in REQUIRED_FIELDS if not data.get(field)]
    if missing:
        return False, {'success': False, 'message': 'حقول ناقصة', 'missing_fields': missing}, 400

    if is_placeholder_name(data.get('full_name')):
        return False, {'success': False, 'message': 'الرجاء إدخال الاسم الكامل الحقيقي'}, 400

    birthday = _parse_birthday(data.get('birthday'))
    if not birthday:
        return False, {'success': False, 'message': 'صيغة تاريخ الميلاد غير صحيحة'}, 400

    user.full_name = data['full_name'].strip()
    user.birthday = birthday
    user.gender = data['gender']
    user.country = data['country']
    details = data.get('profile_details') or {}
    if not isinstance(details, dict):
        return False, {'success': False, 'message': 'Profile details are invalid'}, 400
    required_details = ['nationality', 'profession', 'marital_status', 'marriage_timeline', 'height', 'weight']
    missing_details = [field for field in required_details if not details.get(field)]
    if missing_details:
        return False, {'success': False, 'message': 'Profile fields are missing', 'missing_fields': missing_details}, 400
    profile = UserProfile.query.filter_by(user_id=user.id).first() or UserProfile(user_id=user.id)
    profile.details = details
    db.session.add(profile)
    if 'photo_path' in data:
        user.photo_path = data.get('photo_path') or ''
    return True, None, None


def _upsert_answers(user_id, mcq_data, open_data):
    mcq_answer = MCQAnswer.query.filter_by(user_id=user_id).first() or MCQAnswer(user_id=user_id)
    mcq_answer.q1 = mcq_data.get('q1', mcq_answer.q1 if mcq_answer.id else None)
    mcq_answer.q2 = mcq_data.get('q2', mcq_answer.q2 if mcq_answer.id else None)
    mcq_answer.q3 = mcq_data.get('q3', mcq_answer.q3 if mcq_answer.id else None)
    mcq_answer.q4 = mcq_data.get('q4', mcq_answer.q4 if mcq_answer.id else None)

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

    if is_placeholder_name(data.get('full_name')):
        return jsonify({'success': False, 'message': 'الرجاء إدخال الاسم الكامل الحقيقي'}), 400

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
        full_name=data['full_name'].strip(),
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
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404

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
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404

    data = request.get_json() or {}
    personal = data.get('personal') or data
    mcq_data = data.get('mcq') or {}
    open_data = data.get('open') or {}

    ok, err_body, err_code = _apply_personal_data(user, personal)
    if not ok:
        return jsonify(err_body), err_code

    if not all(open_data.get(f'q{i}') for i in range(1, 5)):
        return jsonify({'success': False, 'message': 'الرجاء الإجابة عن جميع الأسئلة المفتوحة'}), 400

    _upsert_answers(user_id, mcq_data, open_data)
    user.status = 'reviewing'
    db.session.commit()
    sync_user_to_json(user)

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
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404

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
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404

    data = request.get_json() or {}

    for field in UPDATABLE_FIELDS:
        if field in data and data[field] is not None:
            value = data[field]
            if field == 'full_name' and is_placeholder_name(value):
                return jsonify({'success': False, 'message': 'الرجاء إدخال الاسم الكامل الحقيقي'}), 400
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
