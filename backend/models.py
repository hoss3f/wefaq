# backend/models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    """جدول المستخدمين المتقدمين للتعارف"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    birthday = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    guardian_phone = db.Column(db.String(20), nullable=True)
    guardian_relation = db.Column(db.String(50), nullable=True)
    photo_path = db.Column(db.String(200), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='pending')
    status_reason = db.Column(db.Text, nullable=True)
    assigned_admin_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # علاقات لتسهيل الاستخدام في المراحل القادمة
    mcq_answers = db.relationship('MCQAnswer', backref='user', uselist=False, cascade='all, delete-orphan')
    open_answers = db.relationship('OpenAnswer', backref='user', uselist=False, cascade='all, delete-orphan')
    notes = db.relationship('AdminNote', backref='user', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', cascade='all, delete-orphan')


class MCQAnswer(db.Model):
    """إجابات الأسئلة متعددة الخيارات لكل مستخدم"""
    __tablename__ = 'mcq_answers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    q1 = db.Column(db.String(50))
    q2 = db.Column(db.String(50))
    q3 = db.Column(db.String(50))
    q4 = db.Column(db.String(50))


class OpenAnswer(db.Model):
    """إجابات الأسئلة المفتوحة لكل مستخدم"""
    __tablename__ = 'open_answers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    q1 = db.Column(db.Text)
    q2 = db.Column(db.Text)
    q3 = db.Column(db.Text)
    q4 = db.Column(db.Text)


class Admin(db.Model):
    """جدول الإداريين المسؤولين عن مراجعة الطلبات"""
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    city = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_super_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    notes = db.relationship('AdminNote', backref='admin', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='admin', cascade='all, delete-orphan')


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


class Notification(db.Model):
    """إشعارات داخلية للمستخدمين والإداريين"""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)