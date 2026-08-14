# backend/models/db_schemes/admin_note.py
from datetime import datetime
from .base import db


class AdminNote(db.Model):
    """ملاحظات الإداري على مستخدم معين"""
    __tablename__ = 'admin_notes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    note_text = db.Column(db.Text, nullable=False)
    is_visible_to_user = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
