from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required

from backend.app import db
from backend.app.models.contact import ContactMessage
from backend.app.models.prediction import PredictionLog
from backend.app.models.user import User

admin_bp = Blueprint("admin", __name__)


def _require_admin():
    claims = get_jwt()
    return claims.get("role") == "admin"


@admin_bp.get("/users")
@jwt_required()
def list_users():
    if not _require_admin():
        return jsonify({"ok": False, "message": "Admin only"}), 403
    users = [u.to_dict() for u in User.query.order_by(User.id.desc()).all()]
    return jsonify({"ok": True, "users": users})


@admin_bp.get("/predictions")
@jwt_required()
def list_predictions():
    if not _require_admin():
        return jsonify({"ok": False, "message": "Admin only"}), 403
    rows = [p.to_dict() for p in PredictionLog.query.order_by(PredictionLog.id.desc()).limit(200).all()]
    return jsonify({"ok": True, "predictions": rows})


@admin_bp.get("/contacts")
@jwt_required()
def list_contacts():
    if not _require_admin():
        return jsonify({"ok": False, "message": "Admin only"}), 403
    rows = [c.to_dict() for c in ContactMessage.query.order_by(ContactMessage.id.desc()).limit(200).all()]
    return jsonify({"ok": True, "contacts": rows})


@admin_bp.patch("/contacts/<int:contact_id>")
@jwt_required()
def update_contact(contact_id: int):
    if not _require_admin():
        return jsonify({"ok": False, "message": "Admin only"}), 403
    row = ContactMessage.query.get(contact_id)
    if not row:
        return jsonify({"ok": False, "message": "Message not found"}), 404
    payload = request.get_json(silent=True) or {}
    status = str(payload.get("status") or "").strip().lower()
    if status not in ("new", "read", "replied", "archived"):
        return jsonify({"ok": False, "message": "Invalid status"}), 400
    row.status = status
    db.session.commit()
    return jsonify({"ok": True, "contact": row.to_dict()})


@admin_bp.get("/stats")
@jwt_required()
def stats():
    if not _require_admin():
        return jsonify({"ok": False, "message": "Admin only"}), 403
    return jsonify(
        {
            "ok": True,
            "users": User.query.count(),
            "predictions": PredictionLog.query.count(),
            "admins": User.query.filter_by(role="admin").count(),
            "contacts": ContactMessage.query.count(),
            "contacts_new": ContactMessage.query.filter_by(status="new").count(),
        }
    )
