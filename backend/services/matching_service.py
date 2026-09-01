"""Data-driven candidate compatibility calculations."""
from datetime import date
from models import User
from utils import load_questions

OPPOSITE_GENDER = {'ذكر': 'أنثى', 'أنثى': 'ذكر'}


def compute_age(birthday, *, today=None):
    if not birthday:
        return None
    today = today or date.today()
    return today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))


def matching_questions():
    """Questions, not Python constants, define the compatibility inputs."""
    return [q for q in (load_questions() or {}).get('mcq', []) if q.get('matching') is True]


def _answer_for(answer_row, question):
    if not answer_row:
        return None
    key = question.get('answer_key') or f"q{question.get('id')}"
    return (answer_row.answers or {}).get(key) or getattr(answer_row, key, None)


def score_mcq_similarity(mcq_a, mcq_b):
    """Equal-weight, exact-answer percentage; unanswered questions are not applicable."""
    compared = []
    questions = matching_questions()
    for question in questions:
        answer_a, answer_b = _answer_for(mcq_a, question), _answer_for(mcq_b, question)
        if answer_a and answer_b:
            compared.append((question, answer_a, answer_b))
    matches = sum(a == b for _, a, b in compared)
    total = len(compared)
    return {
        'percentage': round(matches / total * 100, 2) if total else 0.0,
        'matching_answers': matches,
        'total_applicable_questions': total,
        'configured_questions': len(questions),
        'breakdown': {str(q.get('id')): {'label': q.get('question'), 'matched': a == b} for q, a, b in compared},
    }


def score_pair(user_a, user_b, mcq_a=None, mcq_b=None, **_):
    """Open answers are deliberately excluded from compatibility at this stage."""
    mcq = score_mcq_similarity(mcq_a or user_a.mcq_answers, mcq_b or user_b.mcq_answers)
    return {
        'compatibility_percentage': mcq['percentage'],
        'total_score': mcq['percentage'],
        'max_score': 100,
        'eligible': user_a.gender != user_b.gender,
        'mandatory_passed': user_a.gender != user_b.gender,
        'stages': {'mcq': mcq},
    }


def _candidate_summary(user, *, private=False):
    details = user.profile.details if user.profile and user.profile.details else {}
    summary = {
        'gender': user.gender, 'country': user.country, 'age': compute_age(user.birthday),
        'nationality': details.get('nationality'), 'profession': details.get('profession'),
        'marital_status': details.get('marital_status'), 'marriage_timeline': details.get('marriage_timeline'),
        'height': details.get('height'),
        'profile_description': user.open_answers.q1 if user.open_answers else None,
    }
    return summary if private else {'id': user.id, 'status': user.status, **summary}


def find_matches_for_user(user, candidates, *, min_score=0, limit=20, include_ineligible=False, private=False):
    opposite = OPPOSITE_GENDER.get(user.gender or '')
    results = []
    for candidate in candidates:
        if candidate.id == user.id or (opposite and candidate.gender != opposite):
            continue
        match = score_pair(user, candidate)
        if not include_ineligible and not match['mandatory_passed']:
            continue
        if match['compatibility_percentage'] >= min_score:
            results.append({'candidate': _candidate_summary(candidate, private=private), **match})
    return sorted(results, key=lambda item: item['compatibility_percentage'], reverse=True)[:limit]
