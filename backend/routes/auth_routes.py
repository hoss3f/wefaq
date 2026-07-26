# backend/routes/auth_routes.py
from flask import Blueprint, request, jsonify
from models import db, User, Admin
from utils import verify_password, user_needs_onboarding

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/user-login', methods=['POST'])
def user_login():
    """تسجيل دخول المستخدم باستخدام الكود الخاص به فقط"""
    data = request.get_json() or {}
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'success': False, 'message': 'الرجاء إدخال الكود'}), 400

    user = User.query.filter_by(code=code).first()
    if not user:
        return jsonify({'success': False, 'message': 'الكود غير صحيح'}), 404

    needs_onboarding = user_needs_onboarding(user)

    return jsonify({
        'success': True,
        'message': 'تم تسجيل الدخول بنجاح',
        'user': {
            'id': user.id,
            'code': user.code,
            'full_name': user.full_name,
            'status': user.status,
            'needs_onboarding': needs_onboarding
        }
    }), 200


@auth_bp.route('/admin-login', methods=['POST'])
def admin_login():
    """تسجيل دخول الإداري باستخدام البريد الإلكتروني وكلمة المرور"""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'success': False, 'message': 'الرجاء إدخال البريد وكلمة المرور'}), 400

    admin = Admin.query.filter_by(email=email).first()
    if not admin or not verify_password(admin.password_hash, password):
        return jsonify({'success': False, 'message': 'البريد أو كلمة المرور غير صحيحة'}), 401

    if not admin.is_active:
        return jsonify({'success': False, 'message': 'هذا الحساب غير مفعّل'}), 403

    return jsonify({
        'success': True,
        'message': 'تم تسجيل الدخول بنجاح',
        'admin': {
            'id': admin.id,
            'full_name': admin.full_name,
            'email': admin.email,
            'city': admin.city,
            'is_super_admin': admin.is_super_admin
        }
    }), 200
