# backend/routes/__init__.py
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp
from routes.notification_routes import notification_bp
from routes.matching_routes import matching_bp


def register_routes(app):
    """تسجيل جميع الـ Blueprints على تطبيق Flask"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(matching_bp)
