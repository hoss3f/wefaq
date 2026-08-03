# backend/routes/notification_routes.py
from flask import Blueprint, jsonify
from models import db, Notification

notification_bp = Blueprint('notification', __name__, url_prefix='/api/notifications')


@notification_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user_notifications(user_id):
    """إرجاع إشعارات مستخدم معيّن، الأحدث أولاً"""
    notifications = Notification.query.filter_by(user_id=user_id) \
        .order_by(Notification.created_at.desc()).all()

    return jsonify({
        'success': True,
        'notifications': [{
            'id': n.id,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat()
        } for n in notifications]
    }), 200


@notification_bp.route('/<int:notification_id>/read', methods=['PUT'])
def mark_as_read(notification_id):
    """تحديد إشعار معيّن كمقروء"""
    notification = Notification.query.get(notification_id)
    if not notification:
        return jsonify({'success': False, 'message': 'الإشعار غير موجود'}), 404

    notification.is_read = True
    db.session.commit()

    return jsonify({'success': True, 'message': 'تم تحديث الإشعار'}), 200
