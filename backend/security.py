# backend/security.py
"""Authentication helpers, authorization checks, and input validation."""
import re
from datetime import date, datetime
from functools import wraps
from flask import request, jsonify
from models import Admin, User

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
# أرقام فقط، مع السماح بعلامة + في البداية لرمز الدولة (E.164)
PHONE_RE = re.compile(r'^\+?[0-9]{6,15}$')
# حرف أبجدي (يشمل العربية) وليس رقماً أو رمزاً
LETTER_RE = re.compile(r'[^\W\d_]', re.UNICODE)

MAX_NAME_LEN = 100
MAX_PHONE_LEN = 20
MAX_EMAIL_LEN = 50
MAX_NOTE_LEN = 2000
MAX_TEXT_LEN = 5000
MIN_ADMIN_PASSWORD_LEN = 8
MIN_AGE = 18
MAX_AGE = 100


def _admin_id_from_request():
    header_val = request.headers.get('X-Admin-Id')
    if header_val and str(header_val).isdigit():
        return int(header_val)
    admin_id = request.args.get('admin_id', type=int)
    if admin_id is not None:
        return admin_id
    if request.is_json:
        data = request.get_json(silent=True) or {}
        raw = data.get('admin_id')
        if raw is not None and str(raw).isdigit():
            return int(raw)
    return None


def get_user_code_from_request():
    code = request.headers.get('X-User-Code', '').strip()
    if code:
        return code
    if request.is_json:
        data = request.get_json(silent=True) or {}
        code = (data.get('code') or '').strip()
        if code:
            return code
    return ''


def get_active_admin(admin_id=None):
    """Return an active admin record or None."""
    if admin_id is None:
        admin_id = _admin_id_from_request()
    if not admin_id:
        return None
    admin = Admin.query.get(admin_id)
    if not admin or not admin.is_active:
        return None
    return admin


def get_active_super_admin(admin_id=None):
    admin = get_active_admin(admin_id)
    if not admin or not admin.is_super_admin:
        return None
    return admin


def get_user_by_code(code=None):
    if code is None:
        code = get_user_code_from_request()
    if not code:
        return None
    return User.query.filter_by(code=code).first()


def unauthorized(message='غير مصرح'):
    return jsonify({'success': False, 'message': message}), 403


def admin_required(f):
    """Require any active admin (header X-Admin-Id or admin_id in query/body)."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not get_active_admin():
            return unauthorized('غير مصرح — يلزم تسجيل دخول إداري')
        return f(*args, **kwargs)
    return wrapped


def super_admin_required(f):
    """Require an active super admin."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not get_active_super_admin():
            return unauthorized('غير مصرح — للمدير العام فقط')
        return f(*args, **kwargs)
    return wrapped


def can_read_user(user_id):
    """
    User may read own profile with X-User-Code; admins may read any profile.
    Returns (user, error_response) — error_response is (body, status) or None.
    """
    user = User.query.get(user_id)
    if not user:
        return None, (jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404)

    if get_active_admin():
        return user, None

    auth_user = get_user_by_code()
    if auth_user and auth_user.id == user_id:
        return user, None

    return None, unauthorized()


def require_user_self(user_id):
    """User must present matching X-User-Code (no admin override for writes)."""
    user = User.query.get(user_id)
    if not user:
        return None, (jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404)

    auth_user = get_user_by_code()
    if not auth_user or auth_user.id != user_id:
        return None, unauthorized()

    return user, None


def can_access_notification(notification):
    """User owns notification, or an active admin."""
    if get_active_admin():
        return True
    auth_user = get_user_by_code()
    return bool(auth_user and notification.user_id == auth_user.id)


def sanitize_text(value, max_len=MAX_TEXT_LEN):
    """Trim and cap length; strip null bytes."""
    if value is None:
        return ''
    text = str(value).replace('\x00', '').strip()
    if len(text) > max_len:
        text = text[:max_len]
    return text


def validate_email(email):
    email = sanitize_text(email, MAX_EMAIL_LEN).lower()
    if not email or not EMAIL_RE.match(email):
        return None
    return email


def validate_phone(value, required=False):
    """قبول أرقام الجوال المكوّنة من أرقام فقط (مع + اختيارية لرمز الدولة).

    ترجع (phone, None) عند النجاح و(None, رسالة الخطأ) عند الفشل.
    """
    phone = sanitize_text(value, MAX_PHONE_LEN)
    if not phone:
        if required:
            return None, 'يرجى إدخال رقم الجوال'
        return '', None
    if not PHONE_RE.match(phone):
        return None, 'رقم الجوال يجب أن يتكوّن من أرقام فقط (6 إلى 15 رقماً)'
    return phone, None


def validate_admin_password(password):
    password = password or ''
    if len(password) < MIN_ADMIN_PASSWORD_LEN:
        return False, f'كلمة المرور يجب أن تكون {MIN_ADMIN_PASSWORD_LEN} أحرف على الأقل'
    return True, None


def validate_birthday(value):
    """تحليل تاريخ الميلاد ورفض التواريخ المستقبلية أو غير المنطقية.

    ترجع (date, None) عند النجاح و(None, رسالة الخطأ) عند الفشل.
    """
    try:
        birthday = datetime.strptime(sanitize_text(value, 10), '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None, 'صيغة تاريخ الميلاد غير صحيحة'

    today = date.today()
    if birthday >= today:
        return None, 'تاريخ الميلاد يجب أن يكون في الماضي'

    age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
    if age < MIN_AGE:
        return None, f'يجب ألا يقل العمر عن {MIN_AGE} سنة'
    if age > MAX_AGE:
        return None, 'تاريخ الميلاد غير صحيح'
    return birthday, None


def validate_text_answer(value, max_len=MAX_TEXT_LEN):
    """الإجابات المفتوحة يجب أن تكون نصاً حقيقياً لا أرقاماً أو رموزاً فقط."""
    text = sanitize_text(value, max_len)
    if not text or not LETTER_RE.search(text):
        return None, 'يرجى كتابة إجابة نصية'
    return text, None
