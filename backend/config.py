# backend/config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')

# تأكد من وجود مجلد instance
os.makedirs(INSTANCE_DIR, exist_ok=True)

SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(INSTANCE_DIR, "wefaq.db")}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

SECRET_KEY = 'wefaq-secret-key-change-in-production'

# الاسم الافتراضي عند توليد كود بدون اسم مخصص
DEFAULT_USER_NAME = 'متقدم جديد'
