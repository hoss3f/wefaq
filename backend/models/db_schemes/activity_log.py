# backend/models/db_schemes/activity_log.py
from datetime import datetime
from .base import db


class ActivityLog(db.Model):
    """سجل إجراءات الإداريين على المستخدمين وإدارة الحسابات"""
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action_type = db.Column(db.String(30), nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship('Admin', foreign_keys=[admin_id])
    user = db.relationship('User', foreign_keys=[user_id])
