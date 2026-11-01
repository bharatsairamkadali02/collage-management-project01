# models/documents.py
from datetime import datetime
from extensions import db


class StudentDocument(db.Model):
    """Uploaded certificates, identity proof, mark sheets, and documents stored in S3."""

    __tablename__ = "student_documents"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    document_type = db.Column(
        db.Enum("photo", "certificate", "id_proof", "marksheet", "other", name="doc_type_enum"),
        nullable=False,
        default="other",
    )
    document_name = db.Column(db.String(255), nullable=False)
    file_key = db.Column(db.String(512), nullable=False)  # S3 Object Key
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)

    uploaded_by_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verification_status = db.Column(
        db.Enum("pending", "verified", "rejected", name="verification_status_enum"),
        default="pending",
        nullable=False,
    )
    verified_by_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verified_at = db.Column(db.DateTime, nullable=True)
    remarks = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    student = db.relationship("Student", back_populates="documents")
    uploaded_by = db.relationship("User", foreign_keys=[uploaded_by_user_id])
    verified_by = db.relationship("User", foreign_keys=[verified_by_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "document_type": self.document_type,
            "document_name": self.document_name,
            "file_key": self.file_key,
            "file_name": self.file_name,
            "verification_status": self.verification_status,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "remarks": self.remarks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
