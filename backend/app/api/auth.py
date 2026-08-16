from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash
import re

from backend.app import db
from backend.app.models.user import User

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    organization = (data.get("organization") or "").strip()

    if not name or not email or not password:
        return jsonify({"ok": False, "message": "Name, email and password are required."}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"ok": False, "message": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"ok": False, "message": "Password must be at least 6 characters."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({
            "ok": False,
            "message": "This email is already registered. Each email can create only one account. Please sign in.",
        }), 409

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        organization=organization,
        role="user",
    )
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"ok": True, "token": token, "user": user.to_dict()}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if email and not EMAIL_RE.match(email):
        return jsonify({"ok": False, "message": "Please enter a valid email address."}), 400
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"ok": False, "message": "Invalid email or password."}), 401
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"ok": True, "token": token, "user": user.to_dict()})


@auth_bp.get("/me")
@jwt_required()
def me():
    uid = int(get_jwt_identity())
    user = User.query.get(uid)
    if not user:
        return jsonify({"ok": False, "message": "User not found."}), 404
    return jsonify({"ok": True, "user": user.to_dict()})
