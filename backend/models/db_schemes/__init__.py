# backend/models/db_schemes/__init__.py
from .base import db
from .user import User, UserProfile
from .mcq_answer import MCQAnswer
from .open_answer import OpenAnswer
from .admin import Admin
from .admin_note import AdminNote
from .notification import Notification
from .activity_log import ActivityLog

__all__ = [
    "db",
    "User",
    "UserProfile",
    "MCQAnswer",
    "OpenAnswer",
    "Admin",
    "AdminNote",
    "Notification",
    "ActivityLog",
]
