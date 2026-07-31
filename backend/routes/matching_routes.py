# backend/routes/matching_routes.py
from flask import Blueprint, request, jsonify
from models import User
from security import admin_required
from services.matching_service import score_pair, find_matches_for_user, _candidate_summary

matching_bp = Blueprint('matching', __name__, url_prefix='/api/admin')

MATCHABLE_STATUSES = ('approved', 'reviewing')


def _parse_int_arg(name: str, default: int, *, minimum: int = 0, maximum: int = 100) -> int:
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(value, maximum))


def _parse_float_arg(name: str, default: float) -> float:
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _parse_bool_arg(name: str, default: bool = False) -> bool:
    raw = request.args.get(name)
    if raw is None:
        return default
    return raw.lower() in ('1', 'true', 'yes')


@matching_bp.route('/users/<int:user_id>/matches', methods=['GET'])
@admin_required
def list_matches_for_user(user_id):
    """Return ranked opposite-gender matches for a user (supervisor workflow)."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'المستخدم غير موجود'}), 404

    status_filter = request.args.get('status', 'approved,reviewing')
    statuses = [s.strip() for s in status_filter.split(',') if s.strip()]
    invalid = [s for s in statuses if s not in MATCHABLE_STATUSES + ('pending', 'rejected')]
    if invalid:
        return jsonify({'success': False, 'message': 'حالة غير صحيحة', 'invalid': invalid}), 400

    query = User.query.filter(User.id != user_id)
    if statuses:
        query = query.filter(User.status.in_(statuses))

    candidates = query.all()
    matches = find_matches_for_user(
        user,
        candidates,
        min_score=_parse_float_arg('min_score', 0),
        limit=_parse_int_arg('limit', 20, minimum=1, maximum=100),
        include_ineligible=_parse_bool_arg('include_ineligible'),
    )

    return jsonify({
        'success': True,
        'user': _candidate_summary(user),
        'count': len(matches),
        'matches': matches,
    }), 200


@matching_bp.route('/matches/pair', methods=['GET'])
@admin_required
def score_user_pair():
    """Score a specific pair of users (for manual comparison in the admin panel)."""
    user_a_id = request.args.get('user_a', type=int)
    user_b_id = request.args.get('user_b', type=int)
    if not user_a_id or not user_b_id:
        return jsonify({'success': False, 'message': 'user_a و user_b مطلوبان'}), 400
    if user_a_id == user_b_id:
        return jsonify({'success': False, 'message': 'لا يمكن مطابقة المستخدم مع نفسه'}), 400

    user_a = User.query.get(user_a_id)
    user_b = User.query.get(user_b_id)
    if not user_a or not user_b:
        return jsonify({'success': False, 'message': 'أحد المستخدمين غير موجود'}), 404

    result = score_pair(user_a, user_b)
    return jsonify({
        'success': True,
        'user_a': _candidate_summary(user_a),
        'user_b': _candidate_summary(user_b),
        'match': result,
    }), 200
