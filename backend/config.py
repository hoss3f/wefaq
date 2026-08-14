# backend/config.py
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

DATA_DIR = os.environ.get('WEFAQ_DATA_DIR', os.path.join(BASE_DIR, 'models', 'data'))
INSTANCE_DIR = os.environ.get('WEFAQ_INSTANCE_DIR', os.path.join(BASE_DIR, 'instance'))
UPLOAD_DIR = os.environ.get('WEFAQ_UPLOAD_DIR', os.path.join(BASE_DIR, 'uploads'))

# تأكد من وجود مجلد instance وسجل النظام
LOGS_DIR = os.path.join(INSTANCE_DIR, 'logs')
os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_PHOTO_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
os.makedirs(LOGS_DIR, exist_ok=True)
SYSTEM_LOG_FILE = os.path.join(LOGS_DIR, 'system.log')

_database_url = os.environ.get('DATABASE_URL', '').strip()
if not _database_url:
    raise RuntimeError(
        'DATABASE_URL is not set. This project uses PostgreSQL only — '
        'set DATABASE_URL in backend/.env (see backend/.env.example).'
    )
# Vercel/Neon/Supabase give postgres:// URLs; SQLAlchemy 2.x requires postgresql://
if _database_url.startswith('postgres://'):
    _database_url = _database_url.replace('postgres://', 'postgresql://', 1)
SQLALCHEMY_DATABASE_URI = _database_url
SQLALCHEMY_TRACK_MODIFICATIONS = False

SECRET_KEY = os.environ.get('SECRET_KEY', 'wefaq-secret-key-change-in-production')

# Runtime options consumed by app.py.  Keep development permissive by default,
# while allowing deployments and tests to override them through environment vars.
CORS_ORIGINS = os.environ.get('WEFAQ_CORS_ORIGINS', '*')
TESTING = os.environ.get('WEFAQ_TESTING', '').strip().lower() in {'1', 'true', 'yes'}

# الاسم الافتراضي عند توليد كود بدون اسم مخصص
DEFAULT_USER_NAME = 'متقدم جديد'
