# backend/utils.py
import json
import logging
import os
import random
import smtplib
import uuid
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash
from config import DATA_DIR, DEFAULT_USER_NAME, UPLOAD_DIR, ALLOWED_PHOTO_EXTENSIONS

logger = logging.getLogger(__name__)


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


def photo_url_for(photo_path):
    """بناء رابط الصورة العامة من اسم الملف المحفوظ"""
    if not photo_path:
        return None

    if photo_path.startswith(('http://', 'https://')):
        return photo_path

    public_base_url = os.environ.get('WEFAQ_PUBLIC_BASE_URL', '').strip().rstrip('/')
    if public_base_url:
        return f"{public_base_url}/uploads/{photo_path.lstrip('/')}"

    from flask import request
    return f"{request.host_url.rstrip('/')}/uploads/{photo_path.lstrip('/')}"


def save_user_photo(file_storage):
    """حفظ صورة المستخدم وإرجاع اسم الملف أو رسالة خطأ"""
    if not file_storage or not file_storage.filename:
        return None, None

    ext = file_storage.filename.rsplit('.', 1)[-1].lower() if '.' in file_storage.filename else ''
    if ext not in ALLOWED_PHOTO_EXTENSIONS:
        return None, 'صيغة الصورة غير مدعومة. المسموح: jpg, jpeg, png, webp'

    filename = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(UPLOAD_DIR, filename))
    return filename, None


import random

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
    from models import OpenAnswer, UserProfile

    name_ok = bool(user.full_name) and not is_placeholder_name(user.full_name)
    profile = UserProfile.query.filter_by(user_id=user.id).first()
    details = profile.details if profile else {}
    profile_ok = all([
        name_ok, user.birthday, user.gender, user.country,
        details.get('nationality'), details.get('profession'),
        details.get('marital_status'), details.get('marriage_timeline'),
        details.get('height'), details.get('weight')
    ])
    if not profile_ok:
        return True

    open_answers = OpenAnswer.query.filter_by(user_id=user.id).first()
    return not open_answers or not all(getattr(open_answers, f'q{i}', None) for i in range(1, 5))


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


def _welcome_email_html(user):
    """بناء محتوى بريد الترحيب بصيغة HTML بالعربية (RTL) بعد إكمال الطلب"""
    name = user.full_name or 'عزيزنا المتقدم'
    return f"""
    <html dir="rtl" lang="ar">
      <body style="font-family: Tahoma, Arial, sans-serif; background-color: #FAF8F4; color: #22302C; padding: 24px;">
        <div style="max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 16px; padding: 32px; border: 1px solid #E5DFD3;">
          <h2 style="color: #1F4741; margin-top: 0;">تم استلام طلبك بنجاح 🌿</h2>
          <p>السلام عليكم ورحمة الله وبركاته، {name}،</p>
          <p>
            نبارك لك إتمام طلب التقدّم في منصة <b>وِفاق</b>. لقد استلمنا جميع بياناتك وإجاباتك بنجاح،
            وسيتولى فريقنا الإداري مراجعة طلبك بعناية واهتمام.
          </p>
          <p>
            نتوقع الرد عليك خلال <b>3 أيام تقريباً</b> من تاريخ التقديم، وستصلك إشعار فور تحديث حالة طلبك.
          </p>
          <blockquote style="border-right: 4px solid #C9A15A; padding-right: 16px; margin: 24px 0; color: #4B5A54; font-style: italic;">
            قال رسول الله ﷺ: «واعلم أنّ النصر مع الصبر، وأنّ الفرج مع الكرب، وأنّ مع العسر يسرًا»
            <br />
            <span style="font-size: 13px; color: #7A867F;">(رواه الترمذي، وقال: حديث حسن صحيح)</span>
          </blockquote>
          <p>
            نسأل الله أن ييسّر لك ما فيه خير لدينك ودنياك، وأن يرزقك شريك الحياة الصالح في وقته المبارك.
          </p>
          <p style="margin-top: 32px;">مع خالص التحية،<br /><b>فريق وِفاق</b></p>
        </div>
      </body>
    </html>
    """


def send_welcome_email(user):
    """
    إرسال بريد ترحيبي للمتقدم بعد إكمال طلبه بنجاح.
    لا يوقف تنفيذ الطلب عند فشل الإرسال أو عدم توفر إعدادات SMTP — يُسجَّل الخطأ فقط.
    """
    if not user.email:
        return

    smtp_host = os.environ.get('SMTP_HOST', '').strip()
    smtp_port = os.environ.get('SMTP_PORT', '').strip()
    smtp_user = os.environ.get('SMTP_USER', '').strip()
    smtp_password = os.environ.get('SMTP_PASSWORD', '')
    smtp_from = os.environ.get('SMTP_FROM', '').strip() or smtp_user

    if not all([smtp_host, smtp_port, smtp_user, smtp_password]):
        logger.warning('إعدادات SMTP غير مكتملة — تم تخطي إرسال بريد الترحيب إلى %s', user.email)
        return

    message = MIMEText(_welcome_email_html(user), 'html', 'utf-8')
    message['Subject'] = 'تم استلام طلبك بنجاح 🌿'
    message['From'] = smtp_from
    message['To'] = user.email

    try:
        with smtplib.SMTP(smtp_host, int(smtp_port), timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from, [user.email], message.as_string())
    except Exception:
        logger.exception('فشل إرسال بريد الترحيب إلى %s', user.email)


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


def _append_system_log(admin_id, user_id, action_type, details):
    """كتابة سطر في ملف سجل النظام (إضافة إلى سجل قاعدة البيانات)"""
    from datetime import datetime
    from config import SYSTEM_LOG_FILE

    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    user_part = user_id if user_id is not None else '-'
    line = (
        f'[{timestamp}] admin_id={admin_id} user_id={user_part} '
        f'action={action_type} details={details or ""}\n'
    )
    with open(SYSTEM_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line)


def log_activity(admin_id, user_id, action_type, details):
    """تسجيل إجراء إداري في قاعدة البيانات وملف سجل النظام (يُكمِت مع الطلب الحالي)"""
    from models import ActivityLog, db

    entry = ActivityLog(
        admin_id=admin_id,
        user_id=user_id,
        action_type=action_type,
        details=details or ''
    )
    db.session.add(entry)
    _append_system_log(admin_id, user_id, action_type, details)
    return entry
