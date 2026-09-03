from flask import Flask, send_from_directory
from flask_cors import CORS
from config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    SECRET_KEY,
    CORS_ORIGINS,
    UPLOAD_DIR,
)
from models import db, Admin, User
from utils import load_admins, load_users, hash_password


def create_app():
    """إنشاء وتهيئة تطبيق Flask، وتسجيل جميع مسارات API"""
    from routes import register_routes

    flask_app = Flask(__name__)

    flask_app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    flask_app.config['SECRET_KEY'] = SECRET_KEY

    cors_kwargs = {"origins": CORS_ORIGINS}

    if CORS_ORIGINS != '*':
        cors_kwargs["supports_credentials"] = True

    cors_kwargs["allow_headers"] = [
        "Content-Type",
        "X-Admin-Id",
        "X-User-Code"
    ]

    CORS(flask_app, resources={r"/api/*": cors_kwargs})

    db.init_app(flask_app)
    register_routes(flask_app)

    @flask_app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(UPLOAD_DIR, filename)

    with flask_app.app_context():
        db.create_all()

    return flask_app


def seed_database():
    """نقل البيانات من ملفات JSON إلى قاعدة بيانات PostgreSQL"""
    with app.app_context():
        # 1. إدراج الإداريين (Admins)
        admins_data = load_admins()
        if admins_data:
            super_admin_data = admins_data.get('super_admin')
            if super_admin_data and not Admin.query.filter_by(email=super_admin_data['email']).first():
                super_admin = Admin(
                    full_name=super_admin_data['full_name'],
                    phone=super_admin_data['phone'],
                    email=super_admin_data['email'],
                    city=super_admin_data['city'],
                    password_hash=hash_password(super_admin_data['password']),
                    is_super_admin=True,
                    is_active=True
                )
                db.session.add(super_admin)

            for admin_info in admins_data.get('admins', []):
                if not Admin.query.filter_by(email=admin_info['email']).first():
                    new_admin = Admin(
                        full_name=admin_info['full_name'],
                        phone=admin_info['phone'],
                        email=admin_info['email'],
                        city=admin_info['city'],
                        password_hash=hash_password(admin_info['password']),
                        is_super_admin=False,
                        is_active=True
                    )
                    db.session.add(new_admin)

            db.session.commit()
            print("تم نقل الإداريين إلى PostgreSQL بنجاح.")

        # 2. إدراج المستخدمين (Users)
        users_data = load_users()
        if users_data:
            inserted = 0
            for entry in users_data:
                code = (entry.get('code') or '').strip()
                if not code or User.query.filter_by(code=code).first():
                    continue

                new_user = User(
                    code=code,
                    full_name=entry.get('full_name', 'متقدم جديد'),
                    phone=entry.get('phone'),
                    email=entry.get('email'),
                    gender=entry.get('gender'),
                    country=entry.get('country'),
                    status=entry.get('status', 'pending')
                )
                db.session.add(new_user)
                inserted += 1

            db.session.commit()
            if inserted > 0:
                print(f"تم نقل {inserted} مستخدمين إلى PostgreSQL بنجاح.")


def test_db_connection():
    """اختبار الاتصال بقاعدة البيانات بدلاً من JSON"""
    with app.app_context():
        admin_count = Admin.query.count()
        user_count = User.query.count()
        print("حالة قاعدة البيانات:")
        print(f" - عدد الإداريين: {admin_count}")
        print(f" - عدد المستخدمين: {user_count}")


app = create_app()

if __name__ == '__main__':
    # شغّل هذا السطر مرة واحدة فقط لنقل البيانات من JSON إلى PostgreSQL، ثم أعد تعليقه
    # seed_database()

    test_db_connection()
    print("\nالخادم جاهز للعمل (يعتمد الآن على PostgreSQL).")
    app.run(debug=True)