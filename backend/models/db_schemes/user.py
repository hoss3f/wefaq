# backend/models/db_schemes/user.py
from datetime import datetime
from .base import db


class User(db.Model):
    """جدول المستخدمين المتقدمين للتعارف"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True) #index true added for faster lookups
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    birthday = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    guardian_phone = db.Column(db.String(20), nullable=True)
    guardian_relation = db.Column(db.String(50), nullable=True)
    photo_path = db.Column(db.String(200), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='pending', index=True)     #index true added for faster lookups
    status_reason = db.Column(db.Text, nullable=True)
    assigned_admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assigned_admin = db.relationship('Admin', foreign_keys=[assigned_admin_id], backref='assigned_users')
    mcq_answers = db.relationship('MCQAnswer', backref='user', uselist=False, cascade='all, delete-orphan')
    open_answers = db.relationship('OpenAnswer', backref='user', uselist=False, cascade='all, delete-orphan')
    notes = db.relationship('AdminNote', backref='user', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', cascade='all, delete-orphan')
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')


class UserProfile(db.Model):
    """Extended one-question-at-a-time onboarding data."""
    __tablename__ = 'user_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    details = db.Column(db.JSON, nullable=False, default=dict)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
