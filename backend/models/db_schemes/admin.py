# backend/models/db_schemes/admin.py
from datetime import datetime
from .base import db


class Admin(db.Model):
    """جدول الإداريين المسؤولين عن مراجعة الطلبات"""
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    city = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_super_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    notes = db.relationship('AdminNote', backref='admin', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='admin', cascade='all, delete-orphan')
