# backend/config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('WEFAQ_DATA_DIR', os.path.join(BASE_DIR, 'data'))
INSTANCE_DIR = os.environ.get('WEFAQ_INSTANCE_DIR', os.path.join(BASE_DIR, 'instance'))
UPLOAD_DIR = os.environ.get('WEFAQ_UPLOAD_DIR', os.path.join(BASE_DIR, 'uploads'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')

# تأكد من وجود مجلد instance وسجل النظام
LOGS_DIR = os.path.join(INSTANCE_DIR, 'logs')
os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_PHOTO_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
os.makedirs(LOGS_DIR, exist_ok=True)
SYSTEM_LOG_FILE = os.path.join(LOGS_DIR, 'system.log')

SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(INSTANCE_DIR, "wefaq.db")}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

SECRET_KEY = 'wefaq-secret-key-change-in-production'

# Runtime options consumed by app.py.  Keep development permissive by default,
# while allowing deployments and tests to override them through environment vars.
CORS_ORIGINS = os.environ.get('WEFAQ_CORS_ORIGINS', '*')
TESTING = os.environ.get('WEFAQ_TESTING', '').strip().lower() in {'1', 'true', 'yes'}

# الاسم الافتراضي عند توليد كود بدون اسم مخصص
DEFAULT_USER_NAME = 'متقدم جديد'
