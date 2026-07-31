# backend/services/matching_service.py
"""Candidate matching logic for the admin/supervisor review workflow."""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from models import User, MCQAnswer, OpenAnswer

GENDER_MALE = 'ذكر'
GENDER_FEMALE = 'أنثى'
OPPOSITE_GENDER = {GENDER_MALE: GENDER_FEMALE, GENDER_FEMALE: GENDER_MALE}

EDUCATION_LEVELS = ['ثانوي', 'دبلوم', 'بكالوريوس', 'ماجستير', 'دكتوراه']
FINANCIAL_LEVELS = ['بسيط', 'متوسط', 'مرتفع', 'لا يهم']
COUNTRY_PREFERENCE = ['نعم', 'لا', 'ليس مهماً']
TRAITS = ['التدين', 'الأخلاق', 'المظهر', 'الثقافة', 'الاستقرار المالي']

MCQ_KEYS = ('q1', 'q2', 'q3', 'q4')
OPEN_KEYS = ('q1', 'q2', 'q3', 'q4')

CONFIDENCE_LABELS = [
    (90, 'ممتاز', 'Excellent Match'),
    (75, 'قوي', 'Strong Match'),
    (60, 'متوسط', 'Moderate Match'),
    (40, 'ضعيف', 'Weak Match'),
    (0, 'ضعيف جداً', 'Poor Match'),
]

# Minimal Arabic stop words for keyword overlap (Stage 3 baseline).
ARABIC_STOP_WORDS = frozenset({
    'في', 'من', 'إلى', 'على', 'أن', 'إن', 'هذا', 'هذه', 'ذلك', 'تلك',
    'التي', 'الذي', 'التى', 'ما', 'لا', 'نعم', 'أو', 'و', 'ب', 'ل',
    'ك', 'هو', 'هي', 'هم', 'هن', 'أنا', 'نحن', 'كان', 'كانت', 'يكون',
    'the', 'a', 'an', 'and', 'or', 'is', 'are', 'to', 'of', 'in', 'for',
})


def compute_age(birthday: date | None, *, today: date | None = None) -> int | None:
    if birthday is None:
        return None
    today = today or date.today()
    age = today.year - birthday.year
    if (today.month, today.day) < (birthday.month, birthday.day):
        age -= 1
    return age


def confidence_label(total_score: float) -> dict[str, str]:
    for minimum, label_ar, label_en in CONFIDENCE_LABELS:
        if total_score >= minimum:
            return {'ar': label_ar, 'en': label_en}
    return {'ar': 'ضعيف جداً', 'en': 'Poor Match'}


def _ordinal_index(value: str | None, ordered: list[str]) -> int | None:
    if not value:
        return None
    try:
        return ordered.index(value)
    except ValueError:
        return None


def _score_gender(user_a: User, user_b: User) -> tuple[float, bool, str]:
    """10 points when genders are opposite; mandatory filter otherwise."""
    if not user_a.gender or not user_b.gender:
        return 0.0, False, 'بيانات الجنس ناقصة'

    if user_a.gender == user_b.gender:
        return 0.0, False, 'نفس الجنس — غير مؤهل'

    expected = OPPOSITE_GENDER.get(user_a.gender)
    if expected and user_b.gender == expected:
        return 10.0, True, 'جنس متعاكس'

    return 0.0, False, 'تركيبة جنس غير صالحة'


def _allows_cross_country(mcq: MCQAnswer | None) -> bool:
    if mcq is None or not mcq.q3:
        return True
    return mcq.q3 != 'لا'


def _score_country(user_a: User, user_b: User, mcq_a: MCQAnswer | None, mcq_b: MCQAnswer | None) -> tuple[float, bool, str]:
    """10 points for same country or when both accept cross-country marriage."""
    if not user_a.country or not user_b.country:
        return 0.0, False, 'بيانات الدولة ناقصة'

    same_country = user_a.country.strip() == user_b.country.strip()
    if same_country:
        return 10.0, True, 'نفس الدولة'

    allows_a = _allows_cross_country(mcq_a)
    allows_b = _allows_cross_country(mcq_b)
    if not allows_a or not allows_b:
        return 0.0, False, 'أحد الطرفين يرفض الزواج من خارج بلده'

    flexible_a = mcq_a and mcq_a.q3 == 'ليس مهماً'
    flexible_b = mcq_b and mcq_b.q3 == 'ليس مهماً'
    if flexible_a or flexible_b:
        return 8.0, True, 'دول مختلفة — أحد الطرفين مرن'

    return 7.0, True, 'دول مختلفة — الطرفان يقبلان'


def _score_age(user_a: User, user_b: User) -> tuple[float, bool, str]:
    """10 points for compatible age gap (absolute gap + traditional direction)."""
    age_a = compute_age(user_a.birthday)
    age_b = compute_age(user_b.birthday)
    if age_a is None or age_b is None:
        return 0.0, False, 'بيانات العمر ناقصة'

    gap = age_a - age_b  # positive => user_a older
    abs_gap = abs(gap)

    if abs_gap <= 3:
        base = 10.0
    elif abs_gap <= 6:
        base = 8.0
    elif abs_gap <= 10:
        base = 6.0
    elif abs_gap <= 15:
        base = 3.0
    else:
        return 0.0, False, f'فارق العمر كبير ({abs_gap} سنة)'

    # Light adjustment when the male is not older (common preference, not a hard rule).
    male, female = (user_a, user_b) if user_a.gender == GENDER_MALE else (user_b, user_a)
    if male.gender == GENDER_MALE and female.gender == GENDER_FEMALE:
        male_age = compute_age(male.birthday)
        female_age = compute_age(female.birthday)
        if male_age is not None and female_age is not None:
            direction_gap = male_age - female_age
            if direction_gap < 0:
                penalty = 2 if direction_gap >= -3 else 4
                base = max(0.0, base - penalty)

    passed = base >= 3.0
    detail = f'فارق العمر {abs_gap} سنة'
    return base, passed, detail


def score_eligibility(
    user_a: User,
    user_b: User,
    mcq_a: MCQAnswer | None = None,
    mcq_b: MCQAnswer | None = None,
) -> dict[str, Any]:
    gender_pts, gender_ok, gender_note = _score_gender(user_a, user_b)
    country_pts, country_ok, country_note = _score_country(user_a, user_b, mcq_a, mcq_b)
    age_pts, age_ok, age_note = _score_age(user_a, user_b)

    mandatory_ok = gender_ok and country_ok
    total = round(gender_pts + country_pts + age_pts, 1)

    return {
        'score': total,
        'max': 30,
        'eligible': mandatory_ok and age_ok,
        'mandatory_passed': mandatory_ok,
        'breakdown': {
            'gender': {'score': gender_pts, 'max': 10, 'passed': gender_ok, 'note': gender_note},
            'country': {'score': country_pts, 'max': 10, 'passed': country_ok, 'note': country_note},
            'age': {'score': age_pts, 'max': 10, 'passed': age_ok, 'note': age_note},
        },
    }


def _score_education_mcq(a: str | None, b: str | None) -> float:
    idx_a = _ordinal_index(a, EDUCATION_LEVELS)
    idx_b = _ordinal_index(b, EDUCATION_LEVELS)
    if idx_a is None or idx_b is None:
        return 0.0
    diff = abs(idx_a - idx_b)
    return {0: 10.0, 1: 8.0, 2: 6.0, 3: 4.0}.get(diff, 2.0)


def _score_financial_mcq(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 10.0
    if a == 'لا يهم' or b == 'لا يهم':
        return 8.0
    idx_a = _ordinal_index(a, FINANCIAL_LEVELS)
    idx_b = _ordinal_index(b, FINANCIAL_LEVELS)
    if idx_a is None or idx_b is None:
        return 4.0
    diff = abs(idx_a - idx_b)
    return 7.0 if diff == 1 else 4.0


def _score_country_pref_mcq(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 10.0
    if a == 'ليس مهماً' or b == 'ليس مهماً':
        return 8.0
    if {a, b} == {'نعم', 'لا'}:
        return 2.0
    return 6.0


def _score_trait_mcq(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 10.0
    if a in TRAITS and b in TRAITS:
        return 3.0
    return 2.0


MCQ_SCORERS = (_score_education_mcq, _score_financial_mcq, _score_country_pref_mcq, _score_trait_mcq)
MCQ_LABELS = ('التعليم', 'المستوى المادي', 'تفضيل الدولة', 'الصفة الأهم')


def score_mcq_similarity(mcq_a: MCQAnswer | None, mcq_b: MCQAnswer | None) -> dict[str, Any]:
    if mcq_a is None or mcq_b is None:
        return {'score': 0.0, 'max': 40, 'breakdown': {}, 'complete': False}

    breakdown = {}
    total = 0.0
    for key, scorer, label in zip(MCQ_KEYS, MCQ_SCORERS, MCQ_LABELS):
        val_a = getattr(mcq_a, key, None)
        val_b = getattr(mcq_b, key, None)
        pts = scorer(val_a, val_b)
        total += pts
        breakdown[key] = {
            'label': label,
            'score': pts,
            'max': 10,
            'answer_a': val_a,
            'answer_b': val_b,
        }

    return {'score': round(total, 1), 'max': 40, 'breakdown': breakdown, 'complete': True}


def _tokenize_arabic(text: str | None) -> set[str]:
    if not text:
        return set()
    cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
    tokens = {t for t in cleaned.split() if len(t) >= 2 and t not in ARABIC_STOP_WORDS}
    return tokens


def _score_open_pair(text_a: str | None, text_b: str | None) -> dict[str, Any]:
    """Keyword overlap + length similarity (Stage 3 baseline — upgradeable to embeddings)."""
    a = (text_a or '').strip()
    b = (text_b or '').strip()
    if not a or not b:
        return {
            'score': 0.0,
            'max': 7.5,
            'keyword_overlap': 0.0,
            'shared_keywords': [],
            'length_ratio': 0.0,
            'needs_manual_review': True,
        }

    tokens_a = _tokenize_arabic(a)
    tokens_b = _tokenize_arabic(b)
    union = tokens_a | tokens_b
    intersection = tokens_a & tokens_b
    overlap = len(intersection) / len(union) if union else 0.0

    len_a, len_b = len(a), len(b)
    length_ratio = min(len_a, len_b) / max(len_a, len_b) if max(len_a, len_b) else 0.0

    if overlap >= 0.5:
        score = 7.5
    elif overlap >= 0.25:
        score = 5.0 + (overlap - 0.25) * 8  # up to ~7
    elif overlap >= 0.1:
        score = 3.0 + (overlap - 0.1) * 13.3
    else:
        score = overlap * 20  # 0–2

    if length_ratio < 0.3:
        score = min(score, 4.0)

    return {
        'score': round(min(score, 7.5), 1),
        'max': 7.5,
        'keyword_overlap': round(overlap, 3),
        'shared_keywords': sorted(intersection)[:20],
        'length_ratio': round(length_ratio, 3),
        'needs_manual_review': True,
    }


OPEN_LABELS = (
    'وصف الذات',
    'توقعات الشريك',
    'رؤية المستقبل',
    'شروط إضافية',
)


def score_open_similarity(open_a: OpenAnswer | None, open_b: OpenAnswer | None) -> dict[str, Any]:
    if open_a is None or open_b is None:
        return {'score': 0.0, 'max': 30, 'breakdown': {}, 'complete': False, 'needs_manual_review': True}

    breakdown = {}
    total = 0.0
    for key, label in zip(OPEN_KEYS, OPEN_LABELS):
        pair = _score_open_pair(getattr(open_a, key, None), getattr(open_b, key, None))
        pair['label'] = label
        breakdown[key] = pair
        total += pair['score']

    return {
        'score': round(total, 1),
        'max': 30,
        'breakdown': breakdown,
        'complete': True,
        'needs_manual_review': True,
    }


def score_pair(
    user_a: User,
    user_b: User,
    mcq_a: MCQAnswer | None = None,
    mcq_b: MCQAnswer | None = None,
    open_a: OpenAnswer | None = None,
    open_b: OpenAnswer | None = None,
) -> dict[str, Any]:
    """Compute full match score between two users."""
    mcq_a = mcq_a if mcq_a is not None else user_a.mcq_answers
    mcq_b = mcq_b if mcq_b is not None else user_b.mcq_answers
    open_a = open_a if open_a is not None else user_a.open_answers
    open_b = open_b if open_b is not None else user_b.open_answers

    eligibility = score_eligibility(user_a, user_b, mcq_a, mcq_b)
    mcq = score_mcq_similarity(mcq_a, mcq_b)
    open_answers = score_open_similarity(open_a, open_b)

    total = round(eligibility['score'] + mcq['score'] + open_answers['score'], 1)
    if not eligibility['mandatory_passed']:
        total = min(total, 39.0)

    label = confidence_label(total)

    return {
        'total_score': total,
        'max_score': 100,
        'confidence': label,
        'eligible': eligibility['eligible'],
        'mandatory_passed': eligibility['mandatory_passed'],
        'stages': {
            'eligibility': eligibility,
            'mcq': mcq,
            'open_answers': open_answers,
        },
    }


def _candidate_summary(user: User) -> dict[str, Any]:
    return {
        'id': user.id,
        'code': user.code,
        'full_name': user.full_name,
        'gender': user.gender,
        'country': user.country,
        'birthday': user.birthday.isoformat() if user.birthday else None,
        'age': compute_age(user.birthday),
        'status': user.status,
    }


def find_matches_for_user(
    user: User,
    candidates: list[User],
    *,
    min_score: float = 0,
    limit: int = 20,
    include_ineligible: bool = False,
) -> list[dict[str, Any]]:
    """Score all candidates against one user and return sorted match results."""
    opposite = OPPOSITE_GENDER.get(user.gender or '')
    results: list[dict[str, Any]] = []

    for candidate in candidates:
        if candidate.id == user.id:
            continue
        if opposite and candidate.gender != opposite:
            continue

        match = score_pair(user, candidate)
        if not include_ineligible and not match['mandatory_passed']:
            continue
        if match['total_score'] < min_score:
            continue

        results.append({
            'candidate': _candidate_summary(candidate),
            **match,
        })

    results.sort(key=lambda r: (r['eligible'], r['total_score']), reverse=True)
    return results[:limit]
