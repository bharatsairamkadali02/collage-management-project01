# models/notifications.py
from datetime import datetime
from extensions import db


class Notification(db.Model):
    """System and role-based notification entity."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(
        db.Enum("academic", "exam", "fee", "general", "urgent", name="notification_type_enum"),
        default="general",
        nullable=False,
    )

    sender_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_role = db.Column(
        db.Enum("all", "admin", "faculty", "student", name="target_role_enum"),
        nullable=True,
    )
    target_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    target_class_section_id = db.Column(
        db.Integer, db.ForeignKey("class_sections.id", ondelete="CASCADE"), nullable=True
    )

    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index("ix_notifications_target_user", "target_user_id", "is_read"),
        db.Index("ix_notifications_created_at", "created_at"),
    )

    # Relationships
    sender = db.relationship("User", foreign_keys=[sender_id], back_populates="sent_notifications")
    target_user = db.relationship("User", foreign_keys=[target_user_id], back_populates="targeted_notifications")
    target_class_section = db.relationship("ClassSection")

    def mark_as_read(self):
        self.is_read = True
        self.read_at = datetime.utcnow()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "sender_name": self.sender.get_full_name() if self.sender else "System",
            "target_role": self.target_role,
            "target_user_id": self.target_user_id,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
