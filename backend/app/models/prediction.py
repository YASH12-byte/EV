from datetime import datetime

from backend.app import db


class PredictionLog(db.Model):
    __tablename__ = "prediction_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    region = db.Column(db.String(80))
    model_name = db.Column(db.String(80))
    input_payload = db.Column(db.Text)
    prediction = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "region": self.region,
            "model_name": self.model_name,
            "prediction": self.prediction,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
