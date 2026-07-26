# backend/routes/admin_routes.py
from flask import Blueprint, request, jsonify
from models import db, User, Admin, AdminNote, Notification

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

VALID_STATUSES = ['pending', 'reviewing', 'approved', 'rejected']


def _require_super_admin(admin_id):
    """التحقق من أن الطلب صادر عن مدير عام نشط"""
    admin = Admin.query.get(admin_id)
    if not admin or not admin.is_active or not admin.is_super_admin:
        return None
    return admin


@admin_bp.route('/users', methods=['GET'])
def list_users():
    """إرجاع قائمة المستخدمين، مع إمكانية التصفية حسب الحالة"""
    status_filter = request.args.get('status')

    query = User.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    users = query.order_by(User.created_at.desc()).all()

    return jsonify({
        'success': True,
        'count': len(users),
        'users': [{
            'id': u.id,
            'code': u.code,
            'full_name': u.full_name,
            'gender': u.gender,
            'country': u.country,
            'birthday': u.birthday.isoformat() if u.birthday else None,
            'status': u.status,
            'assigned_admin_id': u.assigned_admin_id,
            'created_at': u.created_at.isoformat() if u.created_at else None
        } for u in users]
    }), 200


@admin_bp.route('/users/<int:user_id>/status', methods=['PUT'])
def update_status(user_id):
    """تحديث حالة طلب مستخدم، وإرسال إشعار له بالتغيير"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404

    data = request.get_json() or {}
    new_status = data.get('status')
    reason = data.get('status_reason', '')

    if new_status not in VALID_STATUSES:
        return jsonify({'success': False, 'message': 'حالة غير صحيحة'}), 400

    user.status = new_status
    user.status_reason = reason

    notification = Notification(
        user_id=user.id,
        message=f'تم تحديث حالة طلبك إلى: {new_status}'
    )
    db.session.add(notification)
    db.session.commit()

    return jsonify({'success': True, 'message': 'تم تحديث الحالة بنجاح'}), 200


@admin_bp.route('/users/<int:user_id>/notes', methods=['POST'])
def add_note(user_id):
    """إضافة ملاحظة إداري على مستخدم معيّن"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404

    data = request.get_json() or {}
    admin_id = data.get('admin_id')
    note_text = data.get('note_text', '').strip()
    is_visible_to_user = bool(data.get('is_visible_to_user', False))

    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify({'success': False, 'message': 'الإداري غير موجود'}), 404

    if not note_text:
        return jsonify({'success': False, 'message': 'نص الملاحظة مطلوب'}), 400

    note = AdminNote(
        user_id=user_id,
        admin_id=admin_id,
        note_text=note_text,
        is_visible_to_user=is_visible_to_user
    )
    db.session.add(note)
    db.session.commit()

    return jsonify({'success': True, 'message': 'تمت إضافة الملاحظة بنجاح'}), 201


@admin_bp.route('/users/<int:user_id>/notes', methods=['GET'])
def list_notes(user_id):
    """إرجاع كل الملاحظات الخاصة بمستخدم معيّن مع اسم الإداري"""
    notes = (
        AdminNote.query
        .filter_by(user_id=user_id)
        .order_by(AdminNote.created_at.desc())
        .all()
    )

    return jsonify({
        'success': True,
        'notes': [{
            'id': n.id,
            'admin_id': n.admin_id,
            'admin_name': n.admin.full_name if n.admin else None,
            'note_text': n.note_text,
            'is_visible_to_user': n.is_visible_to_user,
            'created_at': n.created_at.isoformat() if n.created_at else None
        } for n in notes]
    }), 200


@admin_bp.route('/create', methods=['POST'])
def create_admin():
    """إنشاء حساب إداري جديد، ومزامنته مع admins.json"""
    from utils import hash_password, sync_admin_to_json

    data = request.get_json() or {}
    required = ['full_name', 'phone', 'email', 'city', 'password']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'success': False, 'message': 'حقول ناقصة', 'missing_fields': missing}), 400

    email = data['email'].lower().strip()
    if Admin.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'البريد الإلكتروني مستخدم مسبقاً'}), 409

    new_admin = Admin(
        full_name=data['full_name'].strip(),
        phone=data['phone'].strip(),
        email=email,
        city=data['city'].strip(),
        password_hash=hash_password(data['password']),
        is_super_admin=False,
        is_active=True
    )
    db.session.add(new_admin)
    db.session.commit()
    sync_admin_to_json(new_admin, plain_password=data['password'])

    return jsonify({'success': True, 'message': 'تم إنشاء حساب الإداري بنجاح', 'admin_id': new_admin.id}), 201


@admin_bp.route('/admins', methods=['GET'])
def list_admins():
    """إرجاع قائمة الإداريين — للمدير العام فقط"""
    admin_id = request.args.get('admin_id', type=int)
    if not _require_super_admin(admin_id):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403

    admins = Admin.query.order_by(Admin.created_at.desc()).all()
    return jsonify({
        'success': True,
        'admins': [{
            'id': a.id,
            'full_name': a.full_name,
            'phone': a.phone,
            'email': a.email,
            'city': a.city,
            'is_super_admin': a.is_super_admin,
            'is_active': a.is_active,
            'created_at': a.created_at.isoformat() if a.created_at else None
        } for a in admins]
    }), 200


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """حذف مستخدم — للمدير العام فقط"""
    from utils import remove_user_from_json

    data = request.get_json() or {}
    admin_id = data.get('admin_id')
    if not _require_super_admin(admin_id):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404

    db.session.delete(user)
    db.session.commit()
    remove_user_from_json(user_id)
    return jsonify({'success': True, 'message': 'تم حذف المستخدم بنجاح'}), 200


@admin_bp.route('/admins/<int:target_id>', methods=['DELETE'])
def delete_admin(target_id):
    """حذف إداري — للمدير العام فقط، مع منع حذف النفس أو المدير العام"""
    from utils import remove_admin_from_json

    data = request.get_json() or {}
    admin_id = data.get('admin_id')
    requester = _require_super_admin(admin_id)
    if not requester:
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403

    if target_id == admin_id:
        return jsonify({'success': False, 'message': 'لا يمكن حذف حسابك'}), 400

    target = Admin.query.get(target_id)
    if not target:
        return jsonify({'success': False, 'message': 'الإداري غير موجود'}), 404

    if target.is_super_admin:
        return jsonify({'success': False, 'message': 'لا يمكن حذف المدير العام'}), 400

    target_email = target.email
    db.session.delete(target)
    db.session.commit()
    remove_admin_from_json(target_email)
    return jsonify({'success': True, 'message': 'تم حذف الإداري بنجاح'}), 200


@admin_bp.route('/users/generate-code', methods=['POST'])
def generate_user_code_route():
    """توليد كود مستخدم جديد، مع اسم اختياري (الافتراضي: متقدم جديد)"""
    from config import DEFAULT_USER_NAME
    from utils import generate_user_code, sync_user_to_json

    data = request.get_json() or {}
    full_name = (data.get('full_name') or '').strip() or DEFAULT_USER_NAME

    new_user = User(
        code=generate_user_code(User),
        full_name=full_name,
        status='pending'
    )
    db.session.add(new_user)
    db.session.commit()
    sync_user_to_json(new_user)

    return jsonify({
        'success': True,
        'message': 'تم توليد كود المستخدم بنجاح',
        'user': {'id': new_user.id, 'code': new_user.code, 'full_name': new_user.full_name}
    }), 201
