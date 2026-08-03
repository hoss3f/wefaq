# backend/app.py
from flask import Flask, send_from_directory
from flask_cors import CORS
from config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    SECRET_KEY,
    CORS_ORIGINS,
    TESTING,
    UPLOAD_DIR,
)
from models import db, Admin
from datetime import datetime
from flask import Flask
from flask_cors import CORS
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY, DEFAULT_USER_NAME
from models import db, Admin, User, MCQAnswer, OpenAnswer
from utils import load_questions, load_admins, load_users, hash_password
from routes import register_routes


def _parse_seed_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def _parse_seed_datetime(value):
    if not value:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(value, fmt)
        except (TypeError, ValueError):
            continue
    return None


def create_app():
    """إنشاء وتهيئة تطبيق Flask، وتسجيل جميع مسارات API"""
    flask_app = Flask(__name__)
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    flask_app.config['SECRET_KEY'] = SECRET_KEY

    cors_kwargs = {"origins": CORS_ORIGINS}
    if CORS_ORIGINS != '*':
        cors_kwargs["supports_credentials"] = True
    cors_kwargs["allow_headers"] = ["Content-Type", "X-Admin-Id", "X-User-Code"]
    CORS(flask_app, resources={r"/api/*": cors_kwargs})
    # السماح لطلبات الواجهة الأمامية (Vite على المنفذ 5173) بالوصول إلى API
    CORS(flask_app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(flask_app)
    register_routes(flask_app)

    @flask_app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(UPLOAD_DIR, filename)

    with flask_app.app_context():
        db.create_all()
        seed_super_admin()
        seed_users_from_json()

    return flask_app


def init_db():
    """إنشاء جداول قاعدة البيانات"""
    with app.app_context():
        db.create_all()
        print("تم إنشاء جداول قاعدة البيانات بنجاح.")


def seed_super_admin():
    """إنشاء حساب المدير العام في قاعدة البيانات من admins.json إن لم يكن موجوداً"""
    admins_data = load_admins()
    if not admins_data or 'super_admin' not in admins_data:
        return

    super_admin_info = admins_data['super_admin']
    existing = Admin.query.filter_by(email=super_admin_info['email']).first()
    if existing:
        return

    new_super_admin = Admin(
        full_name=super_admin_info['full_name'],
        phone=super_admin_info['phone'],
        email=super_admin_info['email'],
        city=super_admin_info.get('city', ''),
        password_hash=hash_password(super_admin_info['password']),
        is_super_admin=True,
        is_active=True
    )
    db.session.add(new_super_admin)
    db.session.commit()
    print("تم إنشاء حساب المدير العام في قاعدة البيانات.")


def seed_users_from_json():
    """إدراج مستخدمين من users.json غير الموجودين في قاعدة البيانات (مطابقة بالكود)"""
    users_data = load_users()
    if not users_data:
        return

    inserted = 0
    for entry in users_data:
        code = (entry.get('code') or '').strip()
        if not code:
            continue
        if User.query.filter_by(code=code).first():
            continue

        full_name = (entry.get('full_name') or '').strip() or DEFAULT_USER_NAME
        new_user = User(
            code=code,
            full_name=full_name,
            phone=entry.get('phone') or None,
            email=entry.get('email') or None,
            birthday=_parse_seed_date(entry.get('birthday')),
            gender=entry.get('gender') or None,
            guardian_phone=entry.get('guardian_phone') or None,
            guardian_relation=entry.get('guardian_relation') or None,
            photo_path=entry.get('photo_path') or None,
            country=entry.get('country') or None,
            status=entry.get('status') or 'pending',
            status_reason=entry.get('status_reason') or None,
            assigned_admin_id=entry.get('assigned_admin_id'),
            created_at=_parse_seed_datetime(entry.get('created_at')) or datetime.utcnow()
        )
        db.session.add(new_user)
        db.session.flush()

        mcq_data = entry.get('mcq_answers') or {}
        if isinstance(mcq_data, dict) and any(mcq_data.get(f'q{i}') for i in range(1, 5)):
            db.session.add(MCQAnswer(
                user_id=new_user.id,
                q1=mcq_data.get('q1'),
                q2=mcq_data.get('q2'),
                q3=mcq_data.get('q3'),
                q4=mcq_data.get('q4')
            ))

        open_data = entry.get('open_answers') or {}
        if isinstance(open_data, dict) and any(open_data.get(f'q{i}') for i in range(1, 5)):
            db.session.add(OpenAnswer(
                user_id=new_user.id,
                q1=open_data.get('q1'),
                q2=open_data.get('q2'),
                q3=open_data.get('q3'),
                q4=open_data.get('q4')
            ))

        inserted += 1

    if inserted:
        db.session.commit()
        print(f"تم إدراج {inserted} مستخدم(ين) من users.json إلى قاعدة البيانات.")


def test_json_loading():
    """اختبار قراءة ملفات JSON الثلاثة"""
    admins = load_admins()
    questions = load_questions()
    users = load_users()

    print("اختبار قراءة الملفات:")
    print(f"  - admins.json: {'موجود' if admins else 'غير موجود'}")
    print(f"  - questions.json: {'موجود' if questions else 'غير موجود'}")
    print(f"  - users.json: {'موجود' if users else 'غير موجود'}")
    if admins and admins.get('super_admin'):
        print(f"  - بريد المدير العام: {admins['super_admin'].get('email')}")

    if questions:
        print(f"  - عدد أسئلة الاختيار من متعدد: {len(questions.get('mcq', []))}")
        print(f"  - عدد الأسئلة المفتوحة: {len(questions.get('open', []))}")


app = create_app()


if __name__ == '__main__':
    test_json_loading()
    print("\nالمرحلة الثانية جاهزة للاختبار.")
    app.run(debug=True)