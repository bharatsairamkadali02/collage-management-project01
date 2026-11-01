# models/fees.py
from datetime import datetime, date
from extensions import db


class FeeRecord(db.Model):
    """Tracks fee dues and fee structure assigned to students for an academic term."""

    __tablename__ = "fee_records"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    semester_id = db.Column(
        db.Integer, db.ForeignKey("semesters.id", ondelete="RESTRICT"), nullable=False
    )
    academic_year_id = db.Column(
        db.Integer, db.ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False
    )

    fee_type = db.Column(
        db.Enum("tuition", "hostel", "library", "exam", "transport", "other", name="fee_type_enum"),
        nullable=False,
        default="tuition",
    )
    description = db.Column(db.String(255), nullable=True)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    amount_paid = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    due_date = db.Column(db.Date, nullable=False)

    payment_status = db.Column(
        db.Enum("pending", "partial", "paid", "overdue", "waived", name="fee_payment_status_enum"),
        nullable=False,
        default="pending",
    )
    waiver_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    waiver_reason = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    student = db.relationship("Student", back_populates="fee_records")
    semester = db.relationship("Semester")
    academic_year = db.relationship("AcademicYear")
    payments = db.relationship("FeePayment", back_populates="fee_record", cascade="all, delete-orphan")

    @property
    def balance_amount(self):
        paid = float(self.amount_paid or 0)
        waiver = float(self.waiver_amount or 0)
        total = float(self.total_amount or 0)
        return max(0.0, total - (paid + waiver))

    @property
    def is_overdue(self):
        if self.payment_status in ("paid", "waived"):
            return False
        return self.due_date < date.today()

    def update_payment_status(self):
        bal = self.balance_amount
        if bal <= 0:
            self.payment_status = "paid"
        elif float(self.amount_paid or 0) > 0:
            self.payment_status = "overdue" if self.is_overdue else "partial"
        else:
            self.payment_status = "overdue" if self.is_overdue else "pending"

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.user.get_full_name() if self.student and self.student.user else None,
            "student_roll": self.student.student_roll_number if self.student else None,
            "fee_type": self.fee_type,
            "description": self.description,
            "total_amount": float(self.total_amount),
            "amount_paid": float(self.amount_paid),
            "balance_amount": self.balance_amount,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "payment_status": self.payment_status,
            "is_overdue": self.is_overdue,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FeePayment(db.Model):
    """Individual payment transaction against a FeeRecord."""

    __tablename__ = "fee_payments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fee_record_id = db.Column(
        db.Integer, db.ForeignKey("fee_records.id", ondelete="CASCADE"), nullable=False
    )
    payment_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    amount_paid = db.Column(db.Numeric(10, 2), nullable=False)
    payment_mode = db.Column(
        db.Enum("cash", "online", "cheque", "dd", "upi", name="payment_mode_enum"),
        nullable=False,
        default="online",
    )
    transaction_reference = db.Column(db.String(100), nullable=True)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False)
    remarks = db.Column(db.String(255), nullable=True)
    received_by_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    fee_record = db.relationship("FeeRecord", back_populates="payments")
    received_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "fee_record_id": self.fee_record_id,
            "payment_date": self.payment_date.isoformat() if self.payment_date else None,
            "amount_paid": float(self.amount_paid),
            "payment_mode": self.payment_mode,
            "transaction_reference": self.transaction_reference,
            "receipt_number": self.receipt_number,
            "remarks": self.remarks,
        }
