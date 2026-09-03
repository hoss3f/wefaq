# backend/models/db_schemes/mcq_answer.py
from .base import db


class MCQAnswer(db.Model):
    """إجابات الأسئلة متعددة الخيارات لكل مستخدم"""
    __tablename__ = 'mcq_answers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    q1 = db.Column(db.String(50))
    q2 = db.Column(db.String(50))
    q3 = db.Column(db.String(50))
    q4 = db.Column(db.String(50))
    # مرجع الإجابات المرن؛ تبقى الأعمدة السابقة لتوافق البيانات الحالية.
    answers = db.Column(db.JSON, nullable=False, default=dict)