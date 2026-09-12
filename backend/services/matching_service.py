"""Deterministic, configuration-driven candidate compatibility calculations."""
from datetime import date
from utils import load_questions

OPPOSITE_GENDER = {'ذكر': 'أنثى', 'أنثى': 'ذكر'}
EMPTY_VALUES = (None, '', [], {})


def compute_age(birthday, *, today=None):
    if not birthday:
        return None
    today = today or date.today()
    return today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))


def _answer_key(item):
    return item.get('answer_key') or (f"q{item['id']}" if item.get('id') is not None else item.get('key'))


def matching_factors(question_data=None):
    """Discover factors from question configuration without depending on IDs or count."""
    data, factors = question_data or load_questions() or {}, []
    for question in data.get('mcq', []):
        if question.get('matching'):
            factors.append({'key': question.get('factor_key') or _answer_key(question), 'label': question.get('question'),
                            'source': 'mcq', 'answer_key': _answer_key(question),
                            **{k: v for k, v in question.items() if k.startswith('matching_') or k == 'weight'}})
    for step in data.get('onboarding', {}).get('steps', []):
        items = step.get('fields', []) if step.get('type') == 'preferences' else [step]
        for item in items:
            if item.get('matching'):
                factors.append({'key': item.get('factor_key') or item.get('key'), 'label': item.get('title'),
                                'source': item.get('storage', 'profile'), 'answer_key': item.get('answer_key') or item.get('key'),
                                **{k: v for k, v in item.items() if k.startswith('matching_') or k in ('min_key', 'max_key', 'weight')}})
    return factors


def _profile_details(user):
    return user.profile.details if getattr(user, 'profile', None) and user.profile.details else {}


def _value(user, source, key):
    if source == 'user':
        return compute_age(getattr(user, 'birthday', None)) if key == 'age' else getattr(user, key, None)
    if source == 'profile':
        return _profile_details(user).get(key)
    if source == 'mcq':
        answers = getattr(user, 'mcq_answers', None)
        if not answers:
            return None
        return (answers.answers or {}).get(key) or getattr(answers, key, None)
    return None


def _valid(value):
    return value not in EMPTY_VALUES


def _bounded(score):
    return max(0.0, min(100.0, float(score)))


def score_exact(a, b, _):
    return 100.0 if a == b else 0.0


def score_ordinal(a, b, config):
    order = config.get('matching_order', [])
    if a in config.get('matching_neutral_options', []) or b in config.get('matching_neutral_options', []):
        return 100.0
    if a not in order or b not in order or len(order) < 2:
        return None
    distance = abs(order.index(a) - order.index(b))
    custom = config.get('matching_distance_scores', {})
    return _bounded(custom[str(distance)]) if str(distance) in custom else _bounded((1 - distance / (len(order) - 1)) * 100)


def score_multi_select(a, b, _):
    if not isinstance(a, (list, tuple, set)) or not isinstance(b, (list, tuple, set)):
        return None
    union = set(a) | set(b)
    return len(set(a) & set(b)) / len(union) * 100 if union else None


def score_boolean(a, b, config):
    truthy = set(config.get('matching_true_values', [True, 'نعم']))
    return 100.0 if (a in truthy) == (b in truthy) else 0.0


def score_numeric(a, b, config):
    try:
        distance, tolerance = abs(float(a) - float(b)), float(config.get('matching_tolerance', 0))
    except (TypeError, ValueError):
        return None
    return (100.0 if distance == 0 else 0.0) if tolerance <= 0 else _bounded((1 - distance / tolerance) * 100)


def score_matrix(a, b, config):
    matrix = config.get('matching_matrix', {})
    score = matrix.get(str(a), {}).get(str(b))
    if score is None:
        score = matrix.get(str(b), {}).get(str(a))
    return _bounded(score) if score is not None else None


SCORERS = {'exact': score_exact, 'ordinal': score_ordinal, 'multi_select': score_multi_select,
           'boolean': score_boolean, 'numeric': score_numeric, 'matrix': score_matrix}


def _range_score(value, lower, upper, tolerance):
    try:
        value, lower, upper, tolerance = map(float, (value, lower, upper, tolerance))
    except (TypeError, ValueError):
        return None
    if lower > upper or tolerance < 0:
        return None
    if lower <= value <= upper:
        return 100.0
    distance = lower - value if value < lower else value - upper
    return 0.0 if tolerance == 0 else _bounded((1 - distance / tolerance) * 100)


def _directional_preference_score(owner, candidate, factor):
    if factor.get('matching_method') == 'preference_range':
        details = _profile_details(owner)
        lower, upper = details.get(factor.get('min_key')), details.get(factor.get('max_key'))
        actual = _value(candidate, factor.get('matching_actual_source', 'profile'), factor.get('matching_actual_key'))
        return _range_score(actual, lower, upper, factor.get('matching_tolerance', 0)) if all(_valid(v) for v in (lower, upper, actual)) else None
    preference = _value(owner, factor.get('source', 'profile'), factor.get('answer_key'))
    actual = _value(candidate, factor.get('matching_actual_source', 'profile'), factor.get('matching_actual_key'))
    if not _valid(preference) or not _valid(actual):
        return None
    preferences = list(preference) if isinstance(preference, (list, tuple, set)) else [preference]
    if any(value in factor.get('matching_neutral_options', []) for value in preferences):
        return 100.0
    aliases = factor.get('matching_aliases', {})
    preferences = [aliases.get(str(value), value) for value in preferences]
    return 100.0 if actual in preferences else 0.0


def _pair_preference_score(user_a, user_b, factor):
    source, key = factor.get('matching_relation_source', 'user'), factor.get('matching_relation_key')
    actual_a, actual_b = _value(user_a, source, key), _value(user_b, source, key)
    if not _valid(actual_a) or not _valid(actual_b):
        return None, []
    scores = factor.get('matching_relation_scores', {}).get('same' if actual_a == actual_b else 'different', {})
    directional = []
    for user in (user_a, user_b):
        preference = _value(user, factor.get('source', 'mcq'), factor.get('answer_key'))
        if _valid(preference) and preference in scores:
            directional.append(_bounded(scores[preference]))
    return ((sum(directional) / len(directional)), directional) if directional else (None, [])


def score_factor(user_a, user_b, factor):
    method = factor.get('matching_method', 'exact')
    if method in ('preference_range', 'preference_exact'):
        directional = [score for score in (_directional_preference_score(user_a, user_b, factor),
                                             _directional_preference_score(user_b, user_a, factor)) if score is not None]
        return ((sum(directional) / len(directional)), directional) if directional else (None, [])
    if method == 'pair_preference':
        return _pair_preference_score(user_a, user_b, factor)
    a, b = _value(user_a, factor.get('source', 'profile'), factor.get('answer_key')), _value(user_b, factor.get('source', 'profile'), factor.get('answer_key'))
    if not _valid(a) or not _valid(b) or method not in SCORERS:
        return None, []
    return SCORERS[method](a, b, factor), []


def evaluate_eligibility(user_a, user_b, *, allowed_statuses=None):
    checks = {
        'different_candidates': getattr(user_a, 'id', None) != getattr(user_b, 'id', None),
        'opposite_gender': OPPOSITE_GENDER.get(getattr(user_a, 'gender', None)) == getattr(user_b, 'gender', None),
        'valid_profiles': all(getattr(u, 'birthday', None) and getattr(u, 'profile', None) for u in (user_a, user_b)),
        'allowed_statuses': True if allowed_statuses is None else all(getattr(u, 'status', None) in allowed_statuses for u in (user_a, user_b)),
    }
    return {'eligible': all(checks.values()), 'checks': checks}


def score_pair(user_a, user_b, *, factors=None, allowed_statuses=None, **_):
    """Score applicable configured factors; eligibility never awards points."""
    eligibility, configured = evaluate_eligibility(user_a, user_b, allowed_statuses=allowed_statuses), factors if factors is not None else matching_factors()
    breakdown, skipped, weighted_total, total_weight = {}, [], 0.0, 0.0
    for factor in configured:
        score, directional = score_factor(user_a, user_b, factor)
        key = str(factor.get('key'))
        weight = max(0.0, float(factor.get('weight', 1.0)))
        if score is None or weight == 0:
            skipped.append(key)
            continue
        score = _bounded(score)
        weighted_total, total_weight = weighted_total + score * weight, total_weight + weight
        breakdown[key] = {'label': factor.get('label'), 'method': factor.get('matching_method', 'exact'), 'score': round(score, 2), 'weight': weight}
        if directional:
            breakdown[key]['directional_scores'] = [round(value, 2) for value in directional]
    has_data = total_weight > 0
    percentage = int(_bounded(round(weighted_total / total_weight))) if has_data else 0
    return {'compatibility_percentage': percentage, 'has_sufficient_data': has_data, 'configured_factors': len(configured),
            'applicable_factors': len(breakdown), 'skipped_factors': skipped, 'breakdown': breakdown,
            'eligible': eligibility['eligible'], 'mandatory_passed': eligibility['eligible'], 'eligibility': eligibility,
            'total_score': percentage, 'max_score': 100}


def _candidate_summary(user, *, private=False):
    details = _profile_details(user)
    open_answers = getattr(user, 'open_answers', None)
    nationality_preference = details.get('nationality_preference')
    if nationality_preference and not isinstance(nationality_preference, list):
        nationality_preference = [nationality_preference]
    summary = {'gender': user.gender, 'country': user.country, 'age': compute_age(user.birthday),
               'nationality': details.get('nationality'), 'education': _value(user, 'mcq', 'q1'),
               'profession': details.get('profession'),
               'marital_status': ({'لم أتزوج من قبل': 'أعزب' if user.gender == 'ذكر' else 'عزباء',
                                   'متزوج سابقاً': 'سبق له الزواج' if user.gender == 'ذكر' else 'سبق لها الزواج'}
                                  .get(details.get('marital_status'), details.get('marital_status'))),
               'marriage_timeline': details.get('marriage_timeline'),
               'has_children': details.get('has_children'), 'kids_count': details.get('kids_count'),
               'height': details.get('height'), 'body_type': details.get('body_type'), 'skin_tone': details.get('skin_tone'),
               'polygyny_acceptance': details.get('polygyny_acceptance'),
               'preferred_age_min': details.get('age_min'), 'preferred_age_max': details.get('age_max'),
               'preferred_nationalities': nationality_preference, 'preferred_marital_status': details.get('marital_preference'),
               'marriage_country_preference': _value(user, 'mcq', 'q3'),
               'partner_priority': _value(user, 'mcq', 'q4'),
               'profile_description': getattr(open_answers, 'q1', None) if open_answers else None,
               'partner_description': getattr(open_answers, 'q2', None) if open_answers else None,
               'marriage_expectations': getattr(open_answers, 'q3', None) if open_answers else None}
    # Public candidates need only an opaque database reference so authenticated
    # users can save or request compatibility without exposing identity fields.
    return {'candidate_ref': user.id, **summary} if private else {'id': user.id, 'code': user.code, 'full_name': user.full_name, 'status': user.status, **summary}


def _public_match(match):
    configured = match['configured_factors']
    completeness = round(match['applicable_factors'] / configured * 100) if configured else 0
    if not match['has_sufficient_data']:
        summary = 'نحتاج إلى معلومات إضافية لإظهار نسبة توافق مفيدة.'
    elif match['applicable_factors'] < configured:
        summary = 'تستند هذه النسبة إلى المعلومات المتاحة حالياً، وما زالت بعض بيانات التفضيلات غير مكتملة.'
    else:
        summary = 'توجد مؤشرات توافق في عدد من التفضيلات المسجلة.'
    return {'candidate': match['candidate'], 'compatibility_percentage': match['compatibility_percentage'],
            'has_sufficient_data': match['has_sufficient_data'], 'applicable_factors': match['applicable_factors'],
            'data_completeness_percentage': completeness, 'compatibility_summary': summary}


def find_matches_for_user(user, candidates, *, min_score=0, limit=20, include_ineligible=False, private=False, allowed_statuses=None):
    results, seen = [], set()
    for candidate in candidates:
        if candidate.id == user.id or candidate.id in seen:
            continue
        seen.add(candidate.id)
        eligibility = evaluate_eligibility(user, candidate, allowed_statuses=allowed_statuses)
        if not include_ineligible and not eligibility['eligible']:
            continue
        match = score_pair(user, candidate, allowed_statuses=allowed_statuses)
        if match['compatibility_percentage'] < min_score:
            continue
        results.append({'candidate': _candidate_summary(candidate, private=private), '_sort_id': candidate.id, **match})
    results.sort(key=lambda item: (-item['compatibility_percentage'], item['_sort_id']))
    for result in results[:limit]:
        result.pop('_sort_id', None)
    return [_public_match(result) for result in results[:limit]] if private else results[:limit]
