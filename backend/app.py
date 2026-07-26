# backend/app.py
from flask import Flask
from flask_cors import CORS
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY
from models import db, Admin
from utils import load_questions, load_admins, load_users, hash_password
from routes import register_routes


def create_app():
    """إنشاء وتهيئة تطبيق Flask، وتسجيل جميع مسارات API"""
    flask_app = Flask(__name__)
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    flask_app.config['SECRET_KEY'] = SECRET_KEY

    # السماح لطلبات الواجهة الأمامية (Vite على المنفذ 5173) بالوصول إلى API
    CORS(flask_app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(flask_app)
    register_routes(flask_app)

    with flask_app.app_context():
        db.create_all()
        seed_super_admin()

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