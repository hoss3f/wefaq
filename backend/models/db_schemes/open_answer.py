# backend/models/db_schemes/open_answer.py
from .base import db


class OpenAnswer(db.Model):
    """إجابات الأسئلة المفتوحة لكل مستخدم"""
    __tablename__ = 'open_answers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    q1 = db.Column(db.Text)
    q2 = db.Column(db.Text)
    q3 = db.Column(db.Text)
    q4 = db.Column(db.Text)
