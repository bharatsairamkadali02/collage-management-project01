# models/audit.py
import json
from datetime import datetime
from extensions import db


class AuditLog(db.Model):
    """System-wide audit trail for sensitive administrative and academic operations."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action = db.Column(db.String(100), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, PUBLISH, etc.
    resource_type = db.Column(db.String(50), nullable=False)  # Student, Faculty, Result, Exam, etc.
    resource_id = db.Column(db.String(50), nullable=True)

    old_values = db.Column(db.Text, nullable=True)  # JSON-encoded
    new_values = db.Column(db.Text, nullable=True)  # JSON-encoded

    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    status = db.Column(
        db.Enum("success", "failure", name="audit_status_enum"),
        default="success",
        nullable=False,
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index("ix_audit_logs_user_date", "user_id", "created_at"),
        db.Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    # Relationships
    user = db.relationship("User", back_populates="audit_logs")

    @classmethod
    def log_action(
        cls,
        user_id,
        action,
        resource_type,
        resource_id=None,
        old_values=None,
        new_values=None,
        ip_address=None,
        user_agent=None,
        status="success",
    ):
        """Helper to create and persist an audit record."""
        try:
            old_json = json.dumps(old_values, default=str) if isinstance(old_values, dict) else old_values
            new_json = json.dumps(new_values, default=str) if isinstance(new_values, dict) else new_values

            log = cls(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id is not None else None,
                old_values=old_json,
                new_values=new_json,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
            )
            db.session.add(log)
            db.session.commit()
            return log
        except Exception:
            db.session.rollback()
            return None

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.get_full_name() if self.user else "System",
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
