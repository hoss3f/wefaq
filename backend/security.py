# backend/security.py
"""Authentication helpers, authorization checks, and input validation."""
import re
from functools import wraps
from flask import request, jsonify
from models import Admin, User

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

MAX_NAME_LEN = 100
MAX_PHONE_LEN = 20
MAX_EMAIL_LEN = 50
MAX_NOTE_LEN = 2000
MAX_TEXT_LEN = 5000
MIN_ADMIN_PASSWORD_LEN = 8


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


def validate_admin_password(password):
    password = password or ''
    if len(password) < MIN_ADMIN_PASSWORD_LEN:
        return False, f'كلمة المرور يجب أن تكون {MIN_ADMIN_PASSWORD_LEN} أحرف على الأقل'
    return True, None
