# backend/config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('WEFAQ_DATA_DIR', os.path.join(BASE_DIR, 'data'))
INSTANCE_DIR = os.environ.get('WEFAQ_INSTANCE_DIR', os.path.join(BASE_DIR, 'instance'))

# تأكد من وجود مجلد instance
os.makedirs(INSTANCE_DIR, exist_ok=True)

SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(INSTANCE_DIR, "wefaq.db")}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

SECRET_KEY = os.environ.get('WEFAQ_SECRET_KEY', 'wefaq-secret-key-change-in-production')

# CORS: comma-separated origins, or * for development
_cors_raw = os.environ.get('WEFAQ_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
CORS_ORIGINS = '*' if _cors_raw.strip() == '*' else [o.strip() for o in _cors_raw.split(',') if o.strip()]

TESTING = os.environ.get('WEFAQ_TESTING', '').lower() in ('1', 'true', 'yes')

# الاسم الافتراضي عند توليد كود بدون اسم مخصص
DEFAULT_USER_NAME = 'متقدم جديد'
