"""Flask application factory for EV Market Growth Prediction System."""
from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import config

db = SQLAlchemy()
jwt = JWTManager()


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(ROOT / "frontend" / "templates"),
        static_folder=str(ROOT / "frontend" / "static"),
        static_url_path="/static",
    )
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = config.JWT_SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False

    CORS(app)
    db.init_app(app)
    jwt.init_app(app)

    from backend.app.api.auth import auth_bp
    from backend.app.api.predict import predict_bp
    from backend.app.api.pages import pages_bp
    from backend.app.api.admin import admin_bp
    from backend.app.api.contact import contact_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(predict_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(contact_bp, url_prefix="/api")

    with app.app_context():
        from backend.app import models as _models  # noqa: F401

        db.create_all()
        _ensure_admin()

    return app


def _ensure_admin():
    from backend.app.models.user import User
    from werkzeug.security import generate_password_hash

    if not User.query.filter_by(email="admin@evforecast.edu").first():
        admin = User(
            name="Project Admin",
            email="admin@evforecast.edu",
            password_hash=generate_password_hash("Admin@123"),
            role="admin",
        )
        db.session.add(admin)
        db.session.commit()
