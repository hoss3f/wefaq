# backend/routes/admin_routes.py
from datetime import datetime
from flask import Blueprint, request, jsonify
from models import db, User, Admin, AdminNote, Notification, ActivityLog, MCQAnswer

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

VALID_STATUSES = ['pending', 'reviewing', 'approved', 'rejected']


def _require_super_admin(admin_id):
    """التحقق من أن الطلب صادر عن مدير عام نشط"""
    admin = Admin.query.get(admin_id)
    if not admin or not admin.is_active or not admin.is_super_admin:
        return None
    return admin


def _require_active_admin(admin_id):
    """التحقق من أن الطلب صادر عن إداري نشط"""
    admin = Admin.query.get(admin_id)
    if not admin or not admin.is_active:
        return None
    return admin


def _user_list_item(user):
    """شكل عنصر المستخدم في قائمة الإداري"""
    return {
        'id': user.id,
        'code': user.code,
        'full_name': user.full_name,
        'gender': user.gender,
        'country': user.country,
        'birthday': user.birthday.isoformat() if user.birthday else None,
        'status': user.status,
        'assigned_admin_id': user.assigned_admin_id,
        'assigned_admin_name': user.assigned_admin.full_name if user.assigned_admin else None,
        'created_at': user.created_at.isoformat() if user.created_at else None
    }


@admin_bp.route('/users', methods=['GET'])
def list_users():
    """إرجاع قائمة المستخدمين مع تصفية اختيارية"""
    status_filter = request.args.get('status')
    scope = request.args.get('scope')
    requesting_admin_id = request.args.get('requesting_admin_id', type=int)
    assigned_admin_id = request.args.get('assigned_admin_id', type=int)
    education = request.args.get('education')
    financial = request.args.get('financial')

    query = User.query

    if status_filter:
        query = query.filter(User.status == status_filter)

    if scope == 'mine' and requesting_admin_id:
        query = query.filter(User.assigned_admin_id == requesting_admin_id)
    elif assigned_admin_id:
        query = query.filter(User.assigned_admin_id == assigned_admin_id)

    if education or financial:
        query = query.join(MCQAnswer, User.id == MCQAnswer.user_id)
        if education:
            query = query.filter(MCQAnswer.q1 == education)
        if financial:
            query = query.filter(MCQAnswer.q2 == financial)

    users = query.order_by(User.created_at.desc()).all()

    return jsonify({
        'success': True,
        'count': len(users),
        'users': [_user_list_item(u) for u in users]
    }), 200


@admin_bp.route('/users/<int:user_id>/status', methods=['PUT'])
def update_status(user_id):
    """تحديث حالة طلب مستخدم، وإرسال إشعار له بالتغيير"""
    from utils import sync_user_to_json, log_activity

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404

    data = request.get_json() or {}
    admin_id = data.get('admin_id')
    new_status = data.get('status')
    reason = data.get('status_reason', '')

    if not _require_active_admin(admin_id):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403

    if new_status not in VALID_STATUSES:
        return jsonify({'success': False, 'message': 'حالة غير صحيحة'}), 400

    old_status = user.status
    user.status = new_status
    user.status_reason = reason

    notification = Notification(
        user_id=user.id,
        message=f'تم تحديث حالة طلبك إلى: {new_status}'
    )
    db.session.add(notification)
    log_activity(
        admin_id,
        user.id,
        'status_change',
        f'من {old_status} إلى {new_status}'
    )
    db.session.commit()
    sync_user_to_json(user)

    return jsonify({'success': True, 'message': 'تم تحديث الحالة بنجاح'}), 200


@admin_bp.route('/users/<int:user_id>/notes', methods=['POST'])
def add_note(user_id):
    """إضافة ملاحظة إداري على مستخدم معيّن"""
    from utils import log_activity

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
    log_activity(
        admin_id,
        user_id,
        'note_added',
        f'is_visible_to_user={is_visible_to_user}'
    )
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


@admin_bp.route('/users/<int:user_id>/assign', methods=['PUT'])
def assign_user_case(user_id):
    """تعيين أو إعادة تعيين مسؤول الحالة"""
    from utils import sync_user_to_json, log_activity

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404

    data = request.get_json() or {}
    admin_id = data.get('admin_id')
    target_admin_id = data.get('target_admin_id')

    requester = _require_active_admin(admin_id)
    if not requester:
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403

    if not requester.is_super_admin and requester.id != user.assigned_admin_id:
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403

    target_admin = Admin.query.get(target_admin_id)
    if not target_admin or not target_admin.is_active:
        return jsonify({'success': False, 'message': 'المسؤول المستهدف غير موجود أو غير نشط'}), 404

    old_admin = user.assigned_admin
    old_label = old_admin.full_name if old_admin else 'غير معيّن'
    user.assigned_admin_id = target_admin_id

    log_activity(
        admin_id,
        user.id,
        'assignment',
        f'من {old_label} إلى {target_admin.full_name}'
    )
    db.session.commit()
    sync_user_to_json(user)

    return jsonify({
        'success': True,
        'message': 'تم تعيين الحالة بنجاح',
        'user': _user_list_item(user)
    }), 200


@admin_bp.route('/logs', methods=['GET'])
def list_activity_logs():
    """إرجاع سجل الإجراءات مع تصفية اختيارية"""
    admin_id = request.args.get('admin_id', type=int)
    if not _require_active_admin(admin_id):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403

    filter_admin_id = request.args.get('filter_admin_id', type=int)
    user_id = request.args.get('user_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = ActivityLog.query

    if filter_admin_id:
        query = query.filter(ActivityLog.admin_id == filter_admin_id)
    if user_id:
        query = query.filter(ActivityLog.user_id == user_id)
    if date_from:
        try:
            dt_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(ActivityLog.created_at >= dt_from)
        except ValueError:
            return jsonify({'success': False, 'message': 'صيغة date_from غير صحيحة'}), 400
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(ActivityLog.created_at <= dt_to)
        except ValueError:
            return jsonify({'success': False, 'message': 'صيغة date_to غير صحيحة'}), 400

    logs = query.order_by(ActivityLog.created_at.desc()).all()

    return jsonify({
        'success': True,
        'count': len(logs),
        'logs': [{
            'id': log.id,
            'admin_id': log.admin_id,
            'admin_name': log.admin.full_name if log.admin else None,
            'user_id': log.user_id,
            'user_name': log.user.full_name if log.user else None,
            'action_type': log.action_type,
            'details': log.details,
            'created_at': log.created_at.isoformat() if log.created_at else None
        } for log in logs]
    }), 200


@admin_bp.route('/create', methods=['POST'])
def create_admin():
    """إنشاء حساب إداري جديد، ومزامنته مع admins.json"""
    from utils import hash_password, sync_admin_to_json, log_activity

    data = request.get_json() or {}
    acting_admin_id = data.get('admin_id')
    if not _require_super_admin(acting_admin_id):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403

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
    db.session.flush()
    sync_admin_to_json(new_admin, plain_password=data['password'])
    log_activity(
        acting_admin_id,
        None,
        'admin_created',
        f'{new_admin.full_name} ({new_admin.email})'
    )
    db.session.commit()

    return jsonify({'success': True, 'message': 'تم إنشاء حساب الإداري بنجاح', 'admin_id': new_admin.id}), 201


@admin_bp.route('/admins', methods=['GET'])
def list_admins():
    """إرجاع قائمة الإداريين — تفاصيل كاملة للمدير العام، أو أسماء فقط للتعيين"""
    admin_id = request.args.get('admin_id', type=int)
    requester = _require_active_admin(admin_id)
    if not requester:
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403

    admins = Admin.query.filter_by(is_active=True).order_by(Admin.created_at.desc()).all()

    if requester.is_super_admin:
        payload = [{
            'id': a.id,
            'full_name': a.full_name,
            'phone': a.phone,
            'email': a.email,
            'city': a.city,
            'is_super_admin': a.is_super_admin,
            'is_active': a.is_active,
            'created_at': a.created_at.isoformat() if a.created_at else None
        } for a in admins]
    else:
        payload = [{'id': a.id, 'full_name': a.full_name} for a in admins]

    return jsonify({'success': True, 'admins': payload}), 200


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """حذف مستخدم — للمدير العام فقط"""
    from utils import remove_user_from_json, log_activity

    data = request.get_json() or {}
    admin_id = data.get('admin_id')
    if not _require_super_admin(admin_id):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404

    user_code = user.code
    user_name = user.full_name
    log_activity(
        admin_id,
        user.id,
        'user_deleted',
        f'{user_name} ({user_code})'
    )
    db.session.delete(user)
    db.session.commit()
    remove_user_from_json(user_id)
    return jsonify({'success': True, 'message': 'تم حذف المستخدم بنجاح'}), 200


@admin_bp.route('/admins/<int:target_id>', methods=['DELETE'])
def delete_admin(target_id):
    """حذف إداري — للمدير العام فقط، مع منع حذف النفس أو المدير العام"""
    from utils import remove_admin_from_json, log_activity

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

    target_name = target.full_name
    target_email = target.email
    log_activity(
        admin_id,
        None,
        'admin_deleted',
        f'{target_name} ({target_email})'
    )
    db.session.delete(target)
    db.session.commit()
    remove_admin_from_json(target_email)
    return jsonify({'success': True, 'message': 'تم حذف الإداري بنجاح'}), 200


@admin_bp.route('/users/generate-code', methods=['POST'])
def generate_user_code_route():
    """توليد كود مستخدم جديد، مع اسم اختياري (الافتراضي: متقدم جديد)"""
    from sqlalchemy.exc import IntegrityError
    from config import DEFAULT_USER_NAME
    from utils import generate_user_code, sync_user_to_json, log_activity

    data = request.get_json() or {}
    full_name = (data.get('full_name') or '').strip() or DEFAULT_USER_NAME
    creator_admin_id = data.get('admin_id')

    try:
        new_user = User(
            code=generate_user_code(User),
            full_name=full_name,
            status='pending'
        )
        if creator_admin_id:
            creator = Admin.query.get(creator_admin_id)
            if creator and creator.is_active:
                new_user.assigned_admin_id = creator_admin_id

        db.session.add(new_user)
        db.session.flush()
        sync_user_to_json(new_user)

        if new_user.assigned_admin_id:
            log_activity(
                creator_admin_id,
                new_user.id,
                'assignment',
                'auto-assigned on code generation'
            )

        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'تعذر توليد كود فريد، حاول مرة أخرى'
        }), 409

    return jsonify({
        'success': True,
        'message': 'تم توليد كود المستخدم بنجاح',
        'user': {'id': new_user.id, 'code': new_user.code, 'full_name': new_user.full_name}
    }), 201
