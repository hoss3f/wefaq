# backend/utils.py
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
from config import DATA_DIR, DEFAULT_USER_NAME


def read_json_file(filename):
    """قراءة ملف JSON من مجلد data"""
    file_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json_file(filename, data):
    """كتابة بيانات إلى ملف JSON في مجلد data"""
    file_path = os.path.join(DATA_DIR, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_admins():
    """تحميل بيانات الإداريين من admins.json"""
    return read_json_file('admins.json')


def load_questions():
    """تحميل الأسئلة من questions.json"""
    return read_json_file('questions.json')


def load_users():
    """تحميل بيانات المستخدمين التجريبية من users.json"""
    return read_json_file('users.json')


def hash_password(raw_password):
    """تشفير كلمة المرور قبل حفظها في قاعدة البيانات"""
    return generate_password_hash(raw_password)


def verify_password(password_hash, raw_password):
    """التحقق من تطابق كلمة المرور مع النسخة المشفرة"""
    return check_password_hash(password_hash, raw_password)


def generate_user_code(user_model):
    """
    توليد كود مستخدم فريد USER###.
    يعتمد على أعلى رقم موجود وليس على عدد الصفوف، لتجنب التعارض بعد حذف مستخدمين.
    """
    max_num = 0
    for (code,) in user_model.query.with_entities(user_model.code).all():
        if not code or not code.startswith('USER'):
            continue
        suffix = code[4:]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))

    next_num = max_num + 1
    candidate = f'USER{next_num:03d}'
    while user_model.query.filter_by(code=candidate).first():
        next_num += 1
        candidate = f'USER{next_num:03d}'
    return candidate


def is_placeholder_name(name):
    """هل الاسم هو الاسم الافتراضي المؤقت؟"""
    return not name or name.strip() == DEFAULT_USER_NAME


def user_needs_onboarding(user, mcq_answer=None):
    """
    المستخدم يحتاج إكمال الطلب إذا نقصت بياناته الأساسية
    أو لم يُجب على الأسئلة بعد (حالة الكود المُولَّد لأول مرة).
    """
    from models import MCQAnswer

    name_ok = bool(user.full_name) and not is_placeholder_name(user.full_name)
    profile_ok = all([
        name_ok,
        user.email,
        user.phone,
        user.birthday,
        user.gender,
        user.country
    ])
    if not profile_ok:
        return True

    mcq = mcq_answer
    if mcq is None:
        mcq = MCQAnswer.query.filter_by(user_id=user.id).first()
    return not mcq or not mcq.q1


def sync_user_to_json(user):
    """إضافة أو تحديث بيانات مستخدم في users.json"""
    users = load_users() or []
    user_dict = {
        'id': user.id,
        'code': user.code,
        'full_name': user.full_name,
        'phone': user.phone or '',
        'email': user.email or '',
        'birthday': user.birthday.isoformat() if user.birthday else '',
        'gender': user.gender or '',
        'guardian_phone': user.guardian_phone or '',
        'guardian_relation': user.guardian_relation or '',
        'photo_path': user.photo_path or '',
        'country': user.country or '',
        'status': user.status,
        'status_reason': user.status_reason or '',
        'assigned_admin_id': user.assigned_admin_id,
        'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else ''
    }

    existing_index = next((i for i, u in enumerate(users) if u.get('id') == user.id), None)
    if existing_index is not None:
        users[existing_index] = user_dict
    else:
        users.append(user_dict)

    write_json_file('users.json', users)


def remove_user_from_json(user_id):
    """حذف مستخدم من users.json"""
    users = load_users() or []
    users = [u for u in users if u.get('id') != user_id]
    write_json_file('users.json', users)


def _normalize_admins_file(data):
    """ضمان بنية admins.json: super_admin + admins[]"""
    if not data:
        data = {}
    if 'admins' not in data or not isinstance(data['admins'], list):
        data['admins'] = []
    if 'super_admin' in data and isinstance(data['super_admin'], dict):
        data['super_admin'].pop('code', None)
    return data


def sync_admin_to_json(admin, plain_password=None):
    """
    إضافة أو تحديث إداري في admins.json.
    كلمة المرور تُحفظ كنص فقط عند الإنشاء (إن وُفرت)، ولا تُستبدل إن لم تُمرَّر.
    """
    data = _normalize_admins_file(load_admins() or {})

    if admin.is_super_admin:
        existing = data.get('super_admin') or {}
        entry = {
            'full_name': admin.full_name,
            'phone': admin.phone,
            'email': admin.email,
            'city': admin.city,
            'password': plain_password if plain_password is not None else existing.get('password', '')
        }
        data['super_admin'] = entry
    else:
        entry = {
            'full_name': admin.full_name,
            'phone': admin.phone,
            'email': admin.email,
            'city': admin.city
        }
        admins_list = data['admins']
        idx = next((i for i, a in enumerate(admins_list) if a.get('email') == admin.email), None)
        if idx is not None:
            if plain_password is not None:
                entry['password'] = plain_password
            else:
                entry['password'] = admins_list[idx].get('password', '')
            admins_list[idx] = entry
        else:
            entry['password'] = plain_password or ''
            admins_list.append(entry)
        data['admins'] = admins_list

    write_json_file('admins.json', data)
    return data


def remove_admin_from_json(email):
    """حذف إداري من قائمة admins في admins.json حسب البريد"""
    data = _normalize_admins_file(load_admins() or {})
    data['admins'] = [a for a in data['admins'] if a.get('email') != email]
    write_json_file('admins.json', data)
    return data


def log_activity(admin_id, user_id, action_type, details):
    """تسجيل إجراء إداري في سجل النشاط (يُكمِت مع الطلب الحالي)"""
    from models import ActivityLog, db

    entry = ActivityLog(
        admin_id=admin_id,
        user_id=user_id,
        action_type=action_type,
        details=details or ''
    )
    db.session.add(entry)
    return entry
