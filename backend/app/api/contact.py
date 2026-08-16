"""Contact form API — stores messages in the database."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request

from backend.app import db
from backend.app.models.contact import ContactMessage

contact_bp = Blueprint("contact", __name__)

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
ROOT = Path(__file__).resolve().parents[3]
BACKUP_DIR = ROOT / "outputs" / "contact"
BACKUP_FILE = BACKUP_DIR / "messages.jsonl"


def _append_backup(row: dict) -> None:
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        with BACKUP_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


@contact_bp.post("/contact")
def submit_contact():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or "").strip()
    email = str(payload.get("email") or "").strip().lower()
    subject = str(payload.get("subject") or "").strip()[:200]
    message = str(payload.get("message") or "").strip()

    if not name or len(name) < 2:
        return jsonify({"ok": False, "message": "Please enter your name."}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"ok": False, "message": "Please enter a valid email address."}), 400
    if not message or len(message) < 5:
        return jsonify({"ok": False, "message": "Please enter a message (at least 5 characters)."}), 400
    if len(message) > 5000:
        return jsonify({"ok": False, "message": "Message is too long (max 5000 characters)."}), 400

    row = ContactMessage(name=name, email=email, subject=subject, message=message, status="new")
    try:
        db.session.add(row)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"ok": False, "message": f"Could not save message: {exc}"}), 500

    data = row.to_dict()
    _append_backup({**data, "saved_at": datetime.now(timezone.utc).isoformat()})
    return jsonify(
        {
            "ok": True,
            "message": "Your message was sent successfully. We will get back to you soon.",
            "id": row.id,
        }
    ), 201
