from flask import Blueprint, jsonify, request
from sqlalchemy import and_, or_

from models import CompatibilityRequest, Notification, SavedCandidate, User, db
from security import get_user_by_code
from services.matching_service import _candidate_summary, evaluate_eligibility, score_pair


match_interaction_bp = Blueprint('match_interactions', __name__, url_prefix='/api/matching')
REQUEST_TRANSITIONS = {
    'pending': {'accepted': 'receiver', 'declined': 'receiver', 'withdrawn': 'sender'},
}


def _approved_user():
    user = get_user_by_code()
    if not user:
        return None, (jsonify({'success': False, 'message': 'يلزم تسجيل الدخول للوصول إلى هذه الصفحة.'}), 403)
    if user.status != 'approved':
        return None, (jsonify({'success': False, 'message': 'تتاح هذه الميزة بعد اعتماد الطلب.'}), 403)
    return user, None


def _eligible_candidate(owner, candidate_id):
    if candidate_id == owner.id:
        return None, (jsonify({'success': False, 'message': 'لا يمكنك اختيار حسابك.'}), 400)
    candidate = User.query.get(candidate_id)
    if not candidate:
        return None, (jsonify({'success': False, 'message': 'المرشح غير متاح.'}), 404)
    eligibility = evaluate_eligibility(owner, candidate, allowed_statuses=('approved',))
    if not eligibility['eligible']:
        return None, (jsonify({'success': False, 'message': 'هذا المرشح غير متاح للتوافق حالياً.'}), 400)
    return candidate, None


def _interaction_candidate(viewer, candidate):
    if not candidate or candidate.status != 'approved':
        return {'available': False, 'candidate': None, 'compatibility_percentage': None}
    eligibility = evaluate_eligibility(viewer, candidate, allowed_statuses=('approved',))
    if not eligibility['eligible']:
        return {'available': False, 'candidate': None, 'compatibility_percentage': None}
    score = score_pair(viewer, candidate, allowed_statuses=('approved',))
    return {
        'available': True,
        'candidate': _candidate_summary(candidate, private=True),
        'compatibility_percentage': score['compatibility_percentage'] if score['has_sufficient_data'] else None,
    }


def _request_payload(item, viewer, direction):
    candidate = item.receiver if direction == 'sent' else item.sender
    return {
        'id': item.id,
        'candidate_ref': candidate.id if candidate else (item.receiver_id if direction == 'sent' else item.sender_id),
        'direction': direction,
        'status': item.status,
        'created_at': item.created_at.isoformat(),
        'updated_at': item.updated_at.isoformat(),
        **_interaction_candidate(viewer, candidate),
    }


@match_interaction_bp.route('/requests', methods=['GET'])
def list_requests():
    user, error = _approved_user()
    if error:
        return error
    rows = CompatibilityRequest.query.filter(
        or_(CompatibilityRequest.sender_id == user.id, CompatibilityRequest.receiver_id == user.id)
    ).order_by(CompatibilityRequest.updated_at.desc()).all()
    incoming = [_request_payload(item, user, 'incoming') for item in rows if item.receiver_id == user.id]
    sent = [_request_payload(item, user, 'sent') for item in rows if item.sender_id == user.id]
    return jsonify({'success': True, 'incoming': incoming, 'sent': sent}), 200


@match_interaction_bp.route('/requests', methods=['POST'])
def create_request():
    user, error = _approved_user()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    try:
        candidate_id = int(data.get('candidate_id'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'المرشح غير صالح.'}), 400
    candidate, error = _eligible_candidate(user, candidate_id)
    if error:
        return error

    existing = CompatibilityRequest.query.filter(or_(
        and_(CompatibilityRequest.sender_id == user.id, CompatibilityRequest.receiver_id == candidate.id),
        and_(CompatibilityRequest.sender_id == candidate.id, CompatibilityRequest.receiver_id == user.id),
    )).first()
    if existing:
        message = 'لديك طلب وارد من هذا المرشح.' if existing.receiver_id == user.id and existing.status == 'pending' else 'سبق تسجيل طلب توافق لهذا المرشح.'
        return jsonify({'success': True, 'message': message, 'request': _request_payload(existing, user, 'incoming' if existing.receiver_id == user.id else 'sent')}), 200

    active_outgoing = CompatibilityRequest.query.filter_by(sender_id=user.id, status='pending').first()
    if active_outgoing:
        return jsonify({
            'success': False,
            'code': 'active_outgoing_request',
            'message': 'لديك طلب توافق قائم حالياً. يمكنك سحبه قبل إرسال طلب جديد.',
        }), 409

    item = CompatibilityRequest(sender_id=user.id, receiver_id=candidate.id, status='pending')
    db.session.add(item)
    db.session.add(Notification(user_id=candidate.id, message='لديك طلب توافق جديد.'))
    db.session.commit()
    return jsonify({'success': True, 'message': 'تم إرسال طلب التوافق.', 'request': _request_payload(item, user, 'sent')}), 201


@match_interaction_bp.route('/requests/<int:request_id>', methods=['PUT'])
def update_request(request_id):
    user, error = _approved_user()
    if error:
        return error
    item = CompatibilityRequest.query.get(request_id)
    if not item:
        return jsonify({'success': False, 'message': 'طلب التوافق غير موجود.'}), 404
    status = (request.get_json(silent=True) or {}).get('status')
    required_actor = REQUEST_TRANSITIONS.get(item.status, {}).get(status)
    if not required_actor:
        return jsonify({'success': False, 'message': 'حالة الطلب غير صالحة.'}), 400
    actor_id = item.sender_id if required_actor == 'sender' else item.receiver_id
    if actor_id != user.id:
        return jsonify({'success': False, 'message': 'لا يمكنك تنفيذ هذا الإجراء على الطلب.'}), 403
    item.status = status
    notices = {
        'accepted': (item.sender_id, 'تم قبول طلب التوافق الذي أرسلته.'),
        'declined': (item.sender_id, 'تم رفض طلب التوافق الذي أرسلته.'),
        'withdrawn': (item.receiver_id, 'تم سحب طلب التوافق الوارد.'),
    }
    notified_user_id, notice = notices[status]
    db.session.add(Notification(user_id=notified_user_id, message=notice))
    db.session.commit()
    messages = {'accepted': 'تم قبول الطلب.', 'declined': 'تم رفض الطلب.', 'withdrawn': 'تم سحب الطلب.'}
    direction = 'sent' if item.sender_id == user.id else 'incoming'
    return jsonify({'success': True, 'message': messages[status], 'request': _request_payload(item, user, direction)}), 200


@match_interaction_bp.route('/saved', methods=['GET'])
def list_saved_candidates():
    user, error = _approved_user()
    if error:
        return error
    rows = SavedCandidate.query.filter_by(user_id=user.id).order_by(SavedCandidate.created_at.desc()).all()
    saved = [{
        'id': item.id,
        'candidate_ref': item.candidate_id,
        'created_at': item.created_at.isoformat(),
        **_interaction_candidate(user, item.candidate),
    } for item in rows]
    return jsonify({'success': True, 'saved': saved}), 200


@match_interaction_bp.route('/saved', methods=['POST'])
def save_candidate():
    user, error = _approved_user()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    try:
        candidate_id = int(data.get('candidate_id'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'المرشح غير صالح.'}), 400
    candidate, error = _eligible_candidate(user, candidate_id)
    if error:
        return error
    item = SavedCandidate.query.filter_by(user_id=user.id, candidate_id=candidate.id).first()
    if not item:
        item = SavedCandidate(user_id=user.id, candidate_id=candidate.id)
        db.session.add(item)
        db.session.commit()
    return jsonify({'success': True, 'message': 'تم حفظ المرشح.', 'saved_id': item.id}), 200


@match_interaction_bp.route('/saved/<int:candidate_id>', methods=['DELETE'])
def remove_saved_candidate(candidate_id):
    user, error = _approved_user()
    if error:
        return error
    item = SavedCandidate.query.filter_by(user_id=user.id, candidate_id=candidate_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'المرشح غير موجود في المحفوظات.'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': 'تمت إزالة المرشح من المحفوظات.'}), 200
